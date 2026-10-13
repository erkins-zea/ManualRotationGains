using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

internal static class TerrainLightingBake
{
    [MenuItem("Tools/Terrain Environment/Bake URP Terrain Lighting")]
    private static void Bake()
    {
        var scene = SceneManager.GetActiveScene();
        if (scene.path != "Assets/TerrainDemoScene_HDRP/Scenes/TerrainDemoScene.unity"
            || SceneManager.sceneCount != 1 || EditorApplication.isPlayingOrWillChangePlaymode
            || Lightmapping.isRunning)
        {
            Debug.LogWarning("Open TerrainDemoScene alone, exit Play mode, and finish any current bake first.");
            return;
        }
        var settings = AssetDatabase.LoadAssetAtPath<LightingSettings>(
            "Assets/Settings/TerrainVR.lighting");
        if (settings == null)
        {
            Debug.LogError("TerrainVR lighting settings have not imported yet.");
            return;
        }
        // The scene's terrain/rocks already contribute GI. Keep the moving XR
        // rig and its controllers dynamic; never apply blanket Static flags.
        Lightmapping.lightingSettings = settings;
        foreach (var root in scene.GetRootGameObjects())
        foreach (var light in root.GetComponentsInChildren<Light>(true))
        {
            if (light.name != "MorningSun") continue;
            Undo.RecordObject(light, "Prepare URP terrain bake");
            light.lightmapBakeType = LightmapBakeType.Mixed;
            light.intensity = 1.3f;
            PrefabUtility.RecordPrefabInstancePropertyModifications(light);
        }
        EditorSceneManager.MarkSceneDirty(scene);
        if (!EditorSceneManager.SaveScene(scene)) return;
        AssetDatabase.SaveAssets();
        if (!Lightmapping.BakeAsync())
            Debug.LogError("Unity could not start the lighting bake. Check the Console and Lighting window.");
        else
            Debug.Log("URP terrain bake started. Follow progress in Window > Rendering > Lighting. Wait for completion, save the scene, then test in Play mode. This is a new URP bake, not the old HDRP lighting.");
    }
}
