The imported environment now uses the existing project's URP renderer.

42 external materials were converted in place, retaining their asset GUIDs so
existing terrain, prefab and scene references continue working. Original materials
and the demo's sun prefab are archived under `Backups/` outside Unity's Assets folder.

Return to Unity and let the changed assets import. Run
**Tools > Terrain Environment > Validate URP Materials** to check loaded shaders;
the same check runs on editor script reload and writes
`Logs/terrain-urp-validation.txt`.

The converted URP Lit materials explicitly disable emission. HDRP left an unused
white `_EmissionColor` in these materials; URP material validation could enable it
and make textured heather or rocks glow white. Both validators now check for this.

If the original demo scene looks washed out or white, its HDRP baked lighting also
needs replacing. The saved demo scene now detaches the old LightingData asset and
uses gradient ambient light. For an already-open copy, run
**Tools > Terrain Environment > Reset Demo Lighting for URP**, then inspect and save.
This command only operates with the demo open by itself; it detaches baked lightmaps
and probes, sets realtime sunlight to 1.3, and disables the imported HDRP reflection
probes. It retains the original baked assets on disk. Rebuild baked lighting in URP
after choosing the final lighting; the reset supplies a realtime starting point.

The Terrain Demo Scene now contains the complete saved SampleScene XR Origin and
XR Interaction Manager, including controller prefabs, tracking, input actions,
interactors, body transformer, locomotion mediator and turn provider. The original
SampleScene is unchanged. TerrainDemoScene is now first in the build scene list.

Manual redirection uses the unchanged hierarchy:
`XR Origin (VR) > Camera Offset > CameraRotationPivot > Main Camera`.
Rotate CameraRotationPivot manually exactly as in SampleScene. No automatic gain
or redirection script was added. The pivot, tracked camera and controller local
transforms and serialized settings were copied without changes.

The demo camera and VirtualCameras group are inactive. SampleScene's duplicate
untracked camera was also retained but deactivated in the terrain copy. XROrigin
now explicitly references the tracked camera, and the turn provider explicitly
references its locomotion mediator. The rig starts near the former demo camera
at (-95.75, -19.5976, 110.77); adjust the XR Origin's world position for your desired
play area and floor height. Its original camera offset is preserved. No automatic
terrain-following, teleportation areas or new locomotion behavior were added.

Reopen TerrainDemoScene in Unity after import to load the merged scene. If Unity
offers to reload the externally modified scene, reload it rather than overwriting
it with the older in-memory copy. Test tracking and manual pivot rotation with the
headset; static checks cannot verify the physical tracking origin or floor height.
Transfer backups are under `Backups/before-terrain-xr-*.zip`. Verify the saved
transfer with `python -B Tools/validate_terrain_xr.py`.

Initial VR performance settings are overridden on the scene's 16 TerrainHigh tiles:
detail distance 25 m, detail density 0.25, terrain basemap distance 200 m, pixel
error 40, tree distance 400 m, billboard start 60 m, maximum full-LOD trees 20.
SpeedTree models use their own LODGroups, so terrain billboard/maximum-tree
settings do not control every tree. Density scaling also depends on each detail
prototype's settings. These are a first tuning pass, not a measured frame-rate
guarantee. Original prefab assets and XR settings are unchanged. Restore the scene
from `Backups/before-terrain-performance-*.zip` to undo the tuning. Reopen the saved
scene to load the overrides; test using the same connection as SampleScene.

For wired Quest Link, the PC performs rendering. `Terrain VR Rendering` is a
separate scene object that applies `Assets/Settings/TerrainVR_RPAsset.asset` in
Play mode and restores the previous quality pipeline and LOD bias on disable.
It never modifies the rig or pivot. The original PC/Mobile pipeline assets are
unchanged. The terrain profile uses Forward rendering, 0.8 render scale, 2x MSAA,
no SSAO/HDR/depth or opaque texture copies, no additional lights, and one 1024px
hard-shadow cascade over 20 m. LOD bias 0.5 selects simpler SpeedTree LODs sooner.
Disable the `Terrain VR Rendering` object outside Play mode to compare performance
with the original renderer. A lower render scale trades sharpness for less work.

To generate new baked lighting, open TerrainDemoScene alone, exit Play mode, and
choose **Tools > Terrain Environment > Bake URP Terrain Lighting**. This saves the
scene, assigns `Assets/Settings/TerrainVR.lighting`, makes MorningSun Mixed, and
starts Unity's asynchronous bake. Follow progress under Window > Rendering >
Lighting, wait for it to finish, then save and test. The preset uses Subtractive
mixed lighting, nondirectional maps, 0.5 texels/m, and reduced sampling/probe cost.
Only static environment objects contribute to lightmaps; the XR rig stays dynamic.
Trees, grass, water, geometry and texture memory still have runtime costs. Baking
is not a substitute for frame-time profiling, nor a guarantee of smooth VR.
Do not run Reset Demo Lighting after baking: that command detaches the new bake.
No lightmaps are generated just by adding the preset or switching renderers.

The scene now uses SampleScene's built-in skybox to fill uncovered background.
The HDRP demo previously had no RenderSettings skybox, so its camera's solid blue
clear color appeared wherever terrain/mountain meshes did not cover the view.
The mountain meshes remain separate scenery. This change does not alter camera
projection, clipping, the XR hierarchy, or gradient ambient lighting. Exit Play
mode and reopen the scene to load it, especially after the temporary magenta
background test. The active camera must use Skybox background, not Solid Color.

Diagnostic test for persistent blue lower-corner patches: TerrainVR_RPAsset now
uses render scale 1.0 instead of the original performance profile's 0.8. This tests
whether resolution scaling contributes to an XR eye-buffer artifact; it is not a
confirmed fix and can increase GPU cost. If it does not help, restore 0.8 and
capture the headset view before further projection or culling changes.

Conversion limitations:
- Water uses a transparent URP Lit material with its original normal texture;
  HDRP depth-dependent color, foam and refraction are not reproduced.
- Layered rocks use their base rock textures; the HDRP moss blending is not reproduced.
- Grass uses two-sided alpha-clipped URP Lit; its custom HDRP wind and terrain color
  blending are not reproduced. Trees use URP SpeedTree8, including billboard materials.
- HDRP volumes, fog, VFX graphs and cinematic camera components in the original demo
  scene were not ported. Use the environment prefabs with your XR scene's lighting.
- The demo sun's Light intensity was changed from 130000 to 1.3 to avoid URP overexposure.
- Headset appearance and performance still need testing in Unity.

Static checks: `python Tools/validate_terrain_materials.py`.
The conversion script is idempotent; already-converted URP materials are skipped.

Dark-scene repair (2026-10-07): disabled the imported Timelines root and its
MainSequence PlayableDirector, including Play On Awake. Its unmuted activation
track 4469521283723661035 targets the Lights group and has no active clips;
the installed Timeline ActivationMixerPlayable sets that target inactive.
The cinematic also animates lighting and the Fader. Disabled the Fader instance
to keep the original cinematic overlay out of the XR scene. Timeline assets
remain intact. Blue sky, trees, grass-off settings, sunlight, and the complete
XR graph are unchanged. Reload TerrainDemoScene outside Play mode to load these
saved changes. Visual confirmation in Unity/headset is still required.

Trees disabled again at user request: all 32 high/proxy terrain overrides use
m_DrawTreesAndFoliage=0. Grass remains off. No foliage assets deleted; XR, camera,
and lighting settings unchanged. Reload the saved scene outside Play mode.
