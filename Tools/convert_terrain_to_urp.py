"""Convert this project's TerrainDemoScene_HDRP materials, retaining their GUIDs.

Dry run: python Tools/convert_terrain_to_urp.py
Apply:   python Tools/convert_terrain_to_urp.py --apply
Original files are archived outside Assets before any writes.
"""
import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'Assets/TerrainDemoScene_HDRP'
SHADERS = {
    'Lit': ('933532a4fcc9baf4fa0491de14d08ed7', 'Shaders/Lit.shader'),
    'Unlit': ('650dd9526735d5b46b79224bc6e94025', 'Shaders/Unlit.shader'),
    'Terrain': ('69c1f799e772cb6438f56c23efccb782', 'Shaders/Terrain/TerrainLit.shader'),
    'Tree': ('99134b1f0c27d54469a840832a28fadf', 'Shaders/Nature/SpeedTree8.shader'),
}
SOURCES = {
    'eb607f5e8fc16e140b732f33d26c8c31': 'Terrain',
    '83570b22fac1fa042ac163344f72821c': 'Tree',
    '0768909a4def7a940821dc16dad27b1c': 'Tree',
    '6e4ae4064600d784cac1e41a9e6f2e59': 'Lit',
    '756bac9090102564582875f4c7e30202': 'Lit',
    '48fe816c3f1833d4d8c09289fe3981cb': 'Rock',
    'dfa3b96612ed4df4a97b7fd06217ba23': 'Grass',
    'dfd4dcd41b27bb44498bfa407660802f': 'Water',
}


def texture(text, name):
    match = re.search(r'^    - ' + re.escape(name) + r':\n((?:        .*\n){3})', text, re.M)
    return match.group(1) if match and 'guid:' in match.group(1) else None


def value(text, name, default):
    match = re.search(r'^    - ' + re.escape(name) + r': ([^\n]+)', text, re.M)
    return match.group(1) if match else str(default)


def set_value(text, name, val, section='m_Floats'):
    pattern = r'^    - ' + re.escape(name) + r': [^\n]+'
    line = f'    - {name}: {val}'
    if re.search(pattern, text, re.M):
        return re.sub(pattern, lambda _: line, text, flags=re.M)
    return text.replace(f'    {section}:\n', f'    {section}:\n{line}\n', 1)


def set_texture(text, name, block):
    if not block:
        return text
    pattern = r'^    - ' + re.escape(name) + r':\n(?:        .*\n){3}'
    entry = f'    - {name}:\n{block}'
    if re.search(pattern, text, re.M):
        return re.sub(pattern, lambda _: entry, text, flags=re.M)
    return text.replace('    m_TexEnvs:\n', '    m_TexEnvs:\n' + entry, 1)


def convert(path, original, kind):
    # Drop obsolete HDRP editor-only subassets, preserving material fileID and .meta.
    material = re.search(r'^--- !u!21 &2100000\nMaterial:\n.*?(?=^--- !u!|\Z)', original, re.M | re.S)
    if not material:
        raise ValueError(f'Unexpected material serialization: {path}')
    text = '%YAML 1.1\n%TAG !u! tag:unity3d.com,2011:\n' + material.group()
    keywords = []
    queue, render_type = 2000, 'Opaque'
    target = kind
    if kind == 'Terrain':
        keywords = ['_TERRAIN_INSTANCED_PERPIXEL_NORMAL']
        if '_TERRAIN_BLEND_HEIGHT' in text:
            keywords.append('_TERRAIN_BLEND_HEIGHT')
            text = set_value(text, '_EnableHeightBlend', 1)
    elif kind == 'Tree':
        queue, render_type = 2450, 'TransparentCutout'
        for prop, keyword in [('_BumpMap', 'EFFECT_BUMP'), ('_ExtraTex', 'EFFECT_EXTRA_TEX'),
                              ('_SubsurfaceTex', 'EFFECT_SUBSURFACE')]:
            if texture(text, prop):
                keywords.append(keyword)
        billboard = value(text, 'EFFECT_BILLBOARD', 0) == '1' or 'Billboard' in path.stem
        if billboard:
            keywords.append('EFFECT_BILLBOARD')
        if value(text, '_HueVariationKwToggle', 0) == '1':
            keywords.append('EFFECT_HUE_VARIATION')
        wind = int(float(value(text, '_WindQuality', 0)))
        keywords.append('_WINDQUALITY_' + ['NONE', 'FASTEST', 'FAST', 'BETTER', 'BEST', 'PALM'][wind])
        text = set_value(text, '_BillboardKwToggle', int(billboard))
        text = set_value(text, '_SubsurfaceKwToggle', int('EFFECT_SUBSURFACE' in keywords))
        text = set_value(text, '_TwoSided', 0 if value(text, '_DoubleSidedEnable', 0) == '1' else 2)
    else:
        target = 'Unlit' if path.stem == 'SkyboxHorizon_Mat' else 'Lit'
        base = texture(text, '_BaseColorMap') or texture(text, '_MainTex')
        normal = texture(text, '_NormalMap') or texture(text, '_BumpMap')
        mask = texture(text, '_MaskMap')
        if kind == 'Grass':
            base = texture(text, 'Texture2D_E1B0D043') or base
            normal = texture(text, 'Texture2D_9DCAAA49') or normal
            mask = texture(text, 'Texture2D_A5E0646') or mask
        elif kind == 'Rock':
            base = texture(text, 'Texture2D_589E2359') or base
            normal = texture(text, 'Texture2D_D8D2DDB3') or normal
            mask = texture(text, 'Texture2D_44625532') or mask
        text = set_texture(text, '_BaseMap', base)
        text = set_texture(text, '_BumpMap', normal)
        if normal and target == 'Lit':
            keywords.append('_NORMALMAP')
        # HDRP mask R=metallic, G=occlusion, A=smoothness also serves URP's maps.
        if mask and target == 'Lit':
            text = set_texture(text, '_MetallicGlossMap', mask)
            text = set_texture(text, '_OcclusionMap', mask)
            keywords += ['_METALLICSPECGLOSSMAP', '_OCCLUSIONMAP']
        clip = value(text, '_AlphaCutoffEnable', 0) == '1'
        if clip:
            keywords.append('_ALPHATEST_ON')
            queue, render_type = 2450, 'TransparentCutout'
        for prop, val in {
            '_Surface': 0, '_Blend': 0, '_SrcBlend': 1, '_DstBlend': 0,
            '_SrcBlendAlpha': 1, '_DstBlendAlpha': 0, '_ZWrite': 1,
            '_Cull': 0 if value(text, '_DoubleSidedEnable', 0) == '1' else 2,
            '_AlphaClip': int(clip), '_Cutoff': value(text, '_AlphaCutoff', 0.5),
            '_WorkflowMode': 1, '_SmoothnessTextureChannel': 0,
            '_BumpScale': value(text, '_NormalScale', 1), '_OcclusionStrength': 1,
            '_Smoothness': value(text, '_SmoothnessRemapMax', 0.5) if mask else value(text, '_Smoothness', 0.5),
            '_ReceiveShadows': 1, '_QueueOffset': 0, '_AlphaToMask': 0,
        }.items():
            text = set_value(text, prop, val)
        if kind == 'Water':
            # Simple transparent water; HDRP depth/refraction graph is not portable.
            queue, render_type = 3000, 'Transparent'
            keywords = ['_SURFACE_TYPE_TRANSPARENT', '_NORMALMAP']
            text = set_texture(text, '_BumpMap', texture(text, '_Normal_Map'))
            for prop, val in {'_Surface': 1, '_SrcBlend': 5, '_DstBlend': 10,
                              '_SrcBlendAlpha': 1, '_DstBlendAlpha': 10,
                              '_ZWrite': 0, '_Cull': 0, '_Smoothness': 0.92,
                              '_Metallic': 0, '_BumpScale': 0.3,
                              '_BlendModePreserveSpecular': 0}.items():
                text = set_value(text, prop, val)
            text = set_value(text, '_BaseColor', '{r: 0.08, g: 0.24, b: 0.28, a: 0.78}', 'm_Colors')
    if target == 'Lit':
        # These environment materials are non-emissive. HDRP's legacy white
        # _EmissionColor is unused there, but URP's inspector enables emission
        # from it when validating the material (even without an emission map).
        text = set_value(text, '_EmissionColor', '{r: 0, g: 0, b: 0, a: 1}', 'm_Colors')
        text = set_value(text, '_EmissionEnabled', 0)
        text = re.sub(r'^  m_LightmapFlags: .*$', '  m_LightmapFlags: 4', text, flags=re.M)
    # Remove stale HDRP texture slots, including missing references from older
    # versions of the pack. The original slots remain available in the backup.
    used_textures = {
        'Lit': {'_BaseMap', '_BumpMap', '_MetallicGlossMap', '_OcclusionMap'},
        'Unlit': {'_BaseMap'},
        'Tree': {'_MainTex', '_BumpMap', '_ExtraTex', '_SubsurfaceTex'},
        'Terrain': set(),  # Terrain supplies layer textures from TerrainData.
    }[target]
    text = re.sub(r'^    - (\S+):\n(?:        .*\n){3}',
                  lambda m: m.group() if m.group(1) in used_textures else '', text, flags=re.M)
    text = text.replace('    m_TexEnvs:\n    m_Ints:', '    m_TexEnvs: []\n    m_Ints:')
    text = re.sub(r'^  m_Shader: .*$', f'  m_Shader: {{fileID: 4800000, guid: {SHADERS[target][0]}, type: 3}}', text, flags=re.M)
    keyword_block = '  m_ValidKeywords:' + ('\n' + ''.join(f'  - {k}\n' for k in keywords) if keywords else ' []\n')
    text = re.sub(r'^  m_ValidKeywords:[^\n]*\n(?:  - .*\n)*', lambda _: keyword_block, text, flags=re.M)
    text = re.sub(r'^  m_InvalidKeywords:[^\n]*\n(?:  - .*\n)*', '  m_InvalidKeywords: []\n', text, flags=re.M)
    text = re.sub(r'^  disabledShaderPasses:[^\n]*\n(?:  - .*\n)*', '  disabledShaderPasses: []\n', text, flags=re.M)
    text = re.sub(r'^  stringTagMap:[^\n]*\n(?:    [^\n]*\n)*', f'  stringTagMap:\n    RenderType: {render_type}\n', text, flags=re.M)
    text = re.sub(r'^  m_CustomRenderQueue: .*$', f'  m_CustomRenderQueue: {queue}', text, flags=re.M)
    return text, target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    package = next((ROOT / 'Library/PackageCache').glob('com.unity.render-pipelines.universal@*'))
    for guid, shader in SHADERS.values():
        assert f'guid: {guid}' in (package / (shader + '.meta')).read_text(), shader
    changes, counts = [], Counter()
    for path in sorted(p for p in PACK.rglob('*') if p.suffix in ('.mat', '.asset')):
        # TerrainData .asset files can be large binary files; only inspect YAML.
        with path.open('rb') as stream:
            if stream.read(5) != b'%YAML':
                continue
        original = path.read_text(encoding='utf-8-sig')
        if '\nMaterial:\n' not in original:
            continue
        guid = re.search(r'm_Shader: \{fileID: [^,]+, guid: (\w+)', original).group(1)
        if guid in {s[0] for s in SHADERS.values()}:
            counts['already URP'] += 1
            continue
        if guid not in SOURCES:
            raise ValueError(f'Unrecognized shader {guid}: {path}')
        converted, target = convert(path, original, SOURCES[guid])
        changes.append((path, converted))
        counts[target] += 1
    print(dict(counts))
    if args.apply and changes:
        backups = ROOT / 'Backups'
        backups.mkdir(exist_ok=True)
        archive = backups / ('terrain-hdrp-materials-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.zip')
        with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as backup:
            for path, _ in changes:
                backup.write(path, path.relative_to(ROOT))
        for path, converted in changes:
            path.write_text(converted, encoding='utf-8', newline='\n')
        print(f'Converted {len(changes)} materials. Originals: {archive.relative_to(ROOT)}')
    elif changes:
        print(f'Dry run: {len(changes)} materials would change. Use --apply to write.')


if __name__ == '__main__':
    main()
