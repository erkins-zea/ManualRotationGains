"""Verify the copied rig, especially the unchanged manual rotation hierarchy."""
import re
import zipfile
from add_sample_xr_to_terrain import ROOT, SOURCE, TARGET, documents, LOCAL

source = documents(SOURCE.read_text())
target = documents(TARGET.read_text())
copied_ids = sorted(k for k in target if 9000000000000 < k < 9000000001000)

# Find the source graph independently from the saved rig and interaction manager.
pending = [k for k, (kind, text) in source.items() if kind == 1 and any(
    f'  m_Name: {n}\n' in text for n in ('XR Origin (VR)', 'XR Interaction Manager'))]
selected = set()
while pending:
    key = pending.pop()
    if not key or key in selected:
        continue
    selected.add(key)
    pending.extend(int(m.group(1)) for m in LOCAL.finditer(source[key][1]))
assert len(selected) == len(copied_ids) == 60
mapping = dict(zip(sorted(selected), copied_ids))
inverse = {v: k for k, v in mapping.items()}
intentional_changes = {72487045, 72487046, 72487050, 1099710212}
for old, new in mapping.items():
    kind, text = target[new]
    normalized = re.sub(r'(^--- !u!\d+ &)-?\d+', lambda m: m.group(1) + str(old), text)
    normalized = LOCAL.sub(lambda m: '{fileID: ' + str(inverse.get(int(m.group(1)), int(m.group(1)))) + '}', normalized)
    if old not in intentional_changes:
        assert (kind, normalized) == source[old], f'Unexpected change to source component {old}'

assert f'm_Camera: {{fileID: {mapping[1327639388]}}}' in target[mapping[72487045]][1]
assert '  m_IsActive: 0\n' in target[mapping[1099710212]][1]
assert 1922094174 not in target, 'Disabled demo camera should have been removed.'
assert f'm_Father: {{fileID: {mapping[929015972]}}}' in target[mapping[1327639384]][1]
assert f'm_Father: {{fileID: {mapping[2017388101]}}}' in target[mapping[929015972]][1]
unresolved = {int(m.group(1)) for m in LOCAL.finditer(TARGET.read_text())} - target.keys() - {0}
assert not unresolved, unresolved

# The original scene must be byte-identical to its pre-transfer backup.
backup = sorted((ROOT / 'Backups').glob('before-terrain-xr-*.zip'))[-1]
with zipfile.ZipFile(backup) as archive:
    assert archive.read(SOURCE.relative_to(ROOT).as_posix()) == SOURCE.read_bytes()
print('PASS: all 60 copied objects/components and local references verified.')
print('PASS: pivot, tracked camera, controllers, input bindings and interaction settings unchanged.')
print('PASS: camera references assigned; spare camera inactive; demo camera removed; SampleScene unchanged.')
