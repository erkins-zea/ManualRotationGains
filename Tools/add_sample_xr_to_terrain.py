"""Copy the saved SampleScene XR object graph into the terrain scene."""
from pathlib import Path
from datetime import datetime
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'Assets/Scenes/SampleScene.unity'
TARGET = ROOT / 'Assets/TerrainDemoScene_HDRP/Scenes/TerrainDemoScene.unity'
HEADER = '%YAML 1.1\n%TAG !u! tag:unity3d.com,2011:\n'
LOCAL = re.compile(r'\{fileID: (-?\d+)\}')


def documents(text):
    return {int(m.group(2)): (int(m.group(1)), m.group()) for m in re.finditer(
        r'^--- !u!(\d+) &(-?\d+)[^\n]*\n.*?(?=^--- !u!|\Z)', text, re.M | re.S)}


def main():
    src = documents(SOURCE.read_text())
    dst = documents(TARGET.read_text())
    if any('  m_Name: XR Origin (VR)\n' in text for _, text in dst.values()):
        raise SystemExit('Terrain scene already contains the XR rig; nothing changed.')
    seeds = [key for key, (kind, text) in src.items() if kind == 1 and
             any(f'  m_Name: {name}\n' in text for name in ('XR Origin (VR)', 'XR Interaction Manager'))]
    assert len(seeds) == 2
    selected = set()
    pending = seeds[:]
    while pending:
        key = pending.pop()
        if key == 0 or key in selected:
            continue
        assert key in src, f'Unresolved source reference: {key}'
        selected.add(key)
        pending.extend(int(m.group(1)) for m in LOCAL.finditer(src[key][1]))
    assert not any(src[k][0] in (29, 104, 157, 196, 1660057539) for k in selected)
    mapping = {key: 9000000000000 + i for i, key in enumerate(sorted(selected), 1)}
    assert not set(mapping.values()) & dst.keys()

    copied = {}
    for key in sorted(selected):
        kind, text = src[key]
        if key == 72487045:  # XROrigin: bind the tracked camera under the rotation pivot.
            text = text.replace('  m_Camera: {fileID: 0}', '  m_Camera: {fileID: 1327639388}')
        if key == 72487050:  # Explicit locomotion mediator reference.
            text = text.replace('  m_Mediator: {fileID: 0}', '  m_Mediator: {fileID: 72487048}')
        if key == 1099710212:  # Preserve the spare camera but keep it inactive.
            text = text.replace('  m_IsActive: 1', '  m_IsActive: 0')
        if key == 72487046:
            text = text.replace('  m_LocalPosition: {x: 0, y: 1.5, z: 0}',
                                '  m_LocalPosition: {x: -95.75, y: -19.5976, z: 110.77}')
        text = re.sub(r'(^--- !u!\d+ &)-?\d+', lambda m: m.group(1) + str(mapping[key]), text)
        text = LOCAL.sub(lambda m: '{fileID: ' + str(mapping.get(int(m.group(1)), int(m.group(1)))) + '}', text)
        copied[mapping[key]] = (kind, text)

    # Disable the demo camera/director hierarchy; retain all environment content.
    disabled = []
    for key, (kind, text) in list(dst.items()):
        if kind == 1 and any(f'  m_Name: {name}\n' in text for name in ('Main Camera', 'VirtualCameras')):
            dst[key] = (kind, text.replace('  m_IsActive: 1', '  m_IsActive: 0'))
            disabled.append(key)
    assert 1922094174 in disabled
    roots_id = next(k for k, (kind, _) in dst.items() if kind == 1660057539)
    roots = dst.pop(roots_id)[1]
    for root in (72487046, 90794026):
        assert root in selected
        roots += f'  - {{fileID: {mapping[root]}}}\n'
    dst.update(copied)
    dst[roots_id] = (1660057539, roots)
    output = HEADER + ''.join(text for _, text in dst.values())
    # Every local reference must resolve after remapping; external asset IDs stay untouched.
    parsed = documents(output)
    assert len(parsed) == len(dst)
    unresolved = {int(m.group(1)) for m in LOCAL.finditer(output)} - parsed.keys() - {0}
    assert not unresolved, f'Unresolved merged references: {unresolved}'

    backup = ROOT / 'Backups' / ('before-terrain-xr-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.zip')
    with zipfile.ZipFile(backup, 'x', zipfile.ZIP_DEFLATED) as archive:
        for path in (SOURCE, TARGET, ROOT / 'ProjectSettings/EditorBuildSettings.asset'):
            archive.write(path, path.relative_to(ROOT))
    TARGET.write_text(output, encoding='utf-8', newline='\n')
    print(f'Copied {len(selected)} serialized objects/components; all local references resolve.')
    print('Rig transform ID:', mapping[72487046], 'Rig object ID:', mapping[72487042])
    print('Original saved scenes backed up to:', backup.relative_to(ROOT))


if __name__ == '__main__':
    main()
