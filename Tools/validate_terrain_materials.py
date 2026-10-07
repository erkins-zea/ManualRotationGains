"""Check converted materials and the environment's serialized renderer references."""
from collections import Counter
from pathlib import Path
import re

from convert_terrain_to_urp import PACK, ROOT, SHADERS, texture, value

guids = {}
for meta in (ROOT / 'Assets').rglob('*.meta'):
    match = re.search(r'^guid: (\w+)', meta.read_text(encoding='utf-8-sig'), re.M)
    if match:
        guids[match.group(1)] = Path(str(meta)[:-5])

errors = []
counts = Counter()
materials = set()
for path in PACK.rglob('*'):
    if path.suffix not in ('.mat', '.asset'):
        continue
    with path.open('rb') as stream:
        if stream.read(5) != b'%YAML':
            continue
    text = path.read_text(encoding='utf-8-sig')
    if '\nMaterial:\n' not in text:
        continue
    materials.add(path)
    shader = re.search(r'm_Shader: \{fileID: 4800000, guid: (\w+)', text)
    kind = next((k for k, v in SHADERS.items() if shader and shader.group(1) == v[0]), None)
    if not kind:
        errors.append(f'Non-URP shader: {path}')
        continue
    counts[kind] += 1
    if kind == 'Lit':
        emission = value(text, '_EmissionColor', '{r: 0, g: 0, b: 0, a: 1}')
        rgb = re.findall(r'[rgb]: ([^,}]+)', emission)
        if any(float(channel) != 0 for channel in rgb) or '\n  - _EMISSION\n' in text:
            errors.append(f'Unexpected emission on non-emissive environment material: {path}')
    if kind != 'Terrain' and path.stem != 'WaterDepthBased':
        if not texture(text, '_MainTex' if kind == 'Tree' else '_BaseMap'):
            errors.append(f'No albedo texture: {path}')
    for guid in re.findall(r'm_Texture: \{fileID: [^,]+, guid: (\w+)', text):
        if guid not in guids or not guids[guid].exists():
            errors.append(f'Missing texture {guid}: {path}')
    for section in ('m_Floats', 'm_Colors', 'm_TexEnvs'):
        block = re.search(r'^    ' + section + r':\n(.*?)(?=^    m_|^  m_|\Z)', text, re.M | re.S)
        names = re.findall(r'^    - (\S+):', block.group(1), re.M) if block else []
        duplicates = [k for k, n in Counter(names).items() if n > 1]
        if duplicates:
            errors.append(f'Duplicate properties {duplicates}: {path}')

references = 0
for path in list(PACK.rglob('*.prefab')) + list(PACK.rglob('*.unity')):
    text = path.read_text(encoding='utf-8-sig')
    for guid in re.findall(r'\{fileID: 2100000, guid: (\w+)', text):
        references += 1
        if guid not in guids or guids[guid] not in materials:
            errors.append(f'Unconverted or unresolved material {guid}: {path}')

print(f'Validated {len(materials)} materials: {dict(counts)}')
print(f'Checked {references} prefab/scene material references and all texture references.')
for error in sorted(set(errors)):
    print(error)
raise SystemExit(1 if errors else 0)
