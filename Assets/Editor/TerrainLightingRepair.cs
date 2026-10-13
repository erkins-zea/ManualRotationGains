using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

internal static class TerrainLightingRepair
{
    private const string DemoScene = "Assets/TerrainDemoScene_HDRP/Scenes/TerrainDemoScene.unity";

    [MenuItem("Tools/Terrain Environment/Reset Demo Lighting for URP")]
    private static void Repair()
    {
        var scene = SceneManager.GetActiveScene();
        if (scene.path != DemoScene || SceneManager.sceneCount != 1)
        {
            Debug.LogWarning("Open TerrainDemoScene by itself to reset its HDRP lighting. Your XR scene's lighting is not changed by this command.");
            return;
        }
        if (EditorApplication.isPlayingOrWillChangePlaymode || Lightmapping.isRunning)
        {
            Debug.LogWarning("Exit Play mode and finish or cancel the lighting bake before resetting lighting.");
            return;
        }
        var pipeline = GraphicsSettings.currentRenderPipeline;
        if (pipeline == null || pipeline.GetType().Name != "UniversalRenderPipelineAsset")
        {
            Debug.LogWarning("This lighting reset requires the project's URP renderer.");
            return;
        }

        // Detach the bake, retaining the original lighting assets on disk.
        Lightmapping.lightingDataAsset = null;
        LightmapSettings.lightmaps = Array.Empty<LightmapData>();
        LightmapSettings.lightProbes = null;
        RenderSettings.ambientMode = AmbientMode.Trilight;
        RenderSettings.ambientSkyColor = new Color(0.212f, 0.227f, 0.259f);
        RenderSettings.ambientEquatorColor = new Color(0.114f, 0.125f, 0.133f);
        RenderSettings.ambientGroundColor = new Color(0.047f, 0.043f, 0.035f);
        RenderSettings.ambientIntensity = 1f;

        int lights = 0, probes = 0;
        foreach (var root in scene.GetRootGameObjects())
        {
            foreach (var light in root.GetComponentsInChildren<Light>(true))
            {
                if (light.name != "MorningSun") continue;
                Undo.RecordObject(light, "Set URP sunlight");
                light.intensity = 1.3f;
                light.lightmapBakeType = LightmapBakeType.Realtime;
                PrefabUtility.RecordPrefabInstancePropertyModifications(light);
                lights++;
            }
            foreach (var probe in root.GetComponentsInChildren<ReflectionProbe>(true))
            {
                var source = PrefabUtility.GetCorrespondingObjectFromSource(probe);
                if (source == null || !AssetDatabase.GetAssetPath(source)
                    .StartsWith("Assets/TerrainDemoScene_HDRP/Prefabs/Lighting/")) continue;
                Undo.RecordObject(probe, "Disable HDRP reflection bake");
                probe.enabled = false;
                PrefabUtility.RecordPrefabInstancePropertyModifications(probe);
                probes++;
            }
        }
        EditorSceneManager.MarkSceneDirty(scene);
        SceneView.RepaintAll();
        Debug.Log($"URP demo lighting reset: detached HDRP bake, adjusted {lights} sun light(s), disabled {probes} imported reflection probes. Save the scene after checking its appearance. Original baked assets remain on disk.");
    }
}
