using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

internal static class TerrainUploadCleanup
{
    const string ScenePath = "Assets/TerrainDemoScene_HDRP/Scenes/TerrainDemoScene.unity";
    const string EnvironmentFolder = "Assets/TerrainDemoScene_HDRP/";
    public static void Audit()
    {
        var scene = EditorSceneManager.OpenScene(ScenePath);
        var report = new StringBuilder();
        foreach (var root in scene.GetRootGameObjects())
        foreach (var t in root.GetComponentsInChildren<Transform>(true))
        {
            if (!t.gameObject.activeSelf)
                report.AppendLine("INACTIVE " + Hierarchy(t));
            foreach (var terrain in t.GetComponents<Terrain>())
                report.AppendLine($"TERRAIN {Hierarchy(t)} foliage={terrain.drawTreesAndFoliage} details={terrain.detailObjectDensity} data={AssetDatabase.GetAssetPath(terrain.terrainData)}");
        }
        Directory.CreateDirectory("Logs");
        File.WriteAllText("Logs/terrain-cleanup-audit.txt", report.ToString());
    }
    static string Hierarchy(Transform t) => t.parent == null ? t.name : Hierarchy(t.parent) + "/" + t.name;

    public static void Validate()
    {
        var scene = EditorSceneManager.OpenScene(ScenePath);
        var roots = scene.GetRootGameObjects();
        var terrains = roots.SelectMany(r => r.GetComponentsInChildren<Terrain>(true)).ToArray();
        if (terrains.Length != 16) throw new Exception("Expected only the 16 working terrain tiles.");
        foreach (var terrain in terrains)
        {
            var data = terrain.terrainData;
            if (data == null || data.treeInstanceCount != 0 || data.treePrototypes.Length != 0 || data.detailPrototypes.Length != 0)
                throw new Exception("Foliage data was not fully removed: " + terrain.name);
            if (data.terrainLayers.Any(l => l == null) || data.heightmapResolution < 2)
                throw new Exception("Terrain surface is missing: " + terrain.name);
            if (terrain.GetComponent<TerrainCollider>()?.terrainData != data)
                throw new Exception("Terrain collider mismatch: " + terrain.name);
        }
        var xr = roots.Single(r => r.name == "XR Origin (VR)");
        if (xr.transform.Find("Camera Offset/CameraRotationPivot/Main Camera")?.GetComponent<Camera>() == null)
            throw new Exception("Tracked camera/pivot hierarchy missing.");
        if (roots.Any(r => r.name == "VirtualCameras" || r.name == "Timelines"))
            throw new Exception("Disabled cinematic roots remain.");
        Directory.CreateDirectory("Logs");
        File.WriteAllText("Logs/terrain-cleanup-validation.txt", "PASS: 16 terrain surfaces/colliders, no tree/grass data, XR camera/pivot present, disabled cinematic roots removed.\n");
        Audit();
    }

    // Batch-only, explicit cleanup entry point; never runs during normal import.
    public static void Clean()
    {
        var scene = EditorSceneManager.OpenScene(ScenePath);
        var report = new StringBuilder();
        var roots = scene.GetRootGameObjects();
        var terrains = roots.SelectMany(r => r.GetComponentsInChildren<Terrain>(true)).ToArray();
        if ((terrains.Length != 32 && terrains.Length != 16) || terrains.Any(t => t.drawTreesAndFoliage || t.detailObjectDensity != 0))
            throw new InvalidOperationException("Expected 16 terrain tiles (optionally 16 disabled proxies) with all foliage already disabled.");

        // Keep XR objects and all LOD children, even if temporarily inactive.
        foreach (var root in roots.Where(r => r.name != "XR Origin (VR)" && r.name != "XR Interaction Manager"))
        foreach (var t in root.GetComponentsInChildren<Transform>(true))
        {
            if (t == null || t.gameObject.activeSelf || t.GetComponentInParent<LODGroup>() != null) continue;
            report.AppendLine("Removed inactive object: " + Hierarchy(t));
            UnityEngine.Object.DestroyImmediate(t.gameObject);
        }

        foreach (var data in terrains.Where(t => t != null).Select(t => t.terrainData).Distinct())
        {
            if (!AssetDatabase.GetAssetPath(data).StartsWith(EnvironmentFolder, StringComparison.Ordinal))
                throw new InvalidOperationException("Unexpected terrain outside environment folder.");
            data.treeInstances = Array.Empty<TreeInstance>();
            data.treePrototypes = Array.Empty<TreePrototype>();
            data.detailPrototypes = Array.Empty<DetailPrototype>();
            data.SetDetailResolution(0, 8);
            EditorUtility.SetDirty(data);
            report.AppendLine("Cleared disabled trees/grass: " + AssetDatabase.GetAssetPath(data));
        }
        EditorSceneManager.MarkSceneDirty(scene);
        if (!EditorSceneManager.SaveScene(scene)) throw new IOException("Could not save cleaned scene.");
        AssetDatabase.SaveAssets();

        // Preserve dependencies of every asset outside the imported environment,
        // all project settings, the working scene, scripts, licenses and Resources.
        // Only prune within the imported environment, never XR sample assets.
        var all = AssetDatabase.GetAllAssetPaths().Where(p => p.StartsWith("Assets/") && File.Exists(p)).ToArray();
        var seeds = all.Where(p => !p.StartsWith(EnvironmentFolder, StringComparison.Ordinal)
            || p == ScenePath || p.EndsWith(".cs") || p.EndsWith(".txt")
            || p.Contains("/Resources/") || p.Contains("/StreamingAssets/")).ToList();
        foreach (var settings in Directory.GetFiles("ProjectSettings"))
        foreach (System.Text.RegularExpressions.Match match in System.Text.RegularExpressions.Regex.Matches(File.ReadAllText(settings), @"guid: ([0-9a-f]{32})"))
        {
            var path = AssetDatabase.GUIDToAssetPath(match.Groups[1].Value);
            if (!string.IsNullOrEmpty(path)) seeds.Add(path);
        }
        var keep = new HashSet<string>(AssetDatabase.GetDependencies(seeds.Distinct().ToArray(), true));
        var remove = all.Where(p => p.StartsWith(EnvironmentFolder, StringComparison.Ordinal) && !keep.Contains(p)).ToArray();
        long bytes = 0;
        foreach (var path in remove)
        {
            var full = Path.GetFullPath(path);
            var allowed = Path.GetFullPath(EnvironmentFolder).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (!full.StartsWith(allowed, StringComparison.OrdinalIgnoreCase)) throw new IOException("Unsafe delete path.");
            bytes += new FileInfo(path).Length;
            report.AppendLine("Removed unused asset: " + path);
            if (!AssetDatabase.DeleteAsset(path)) throw new IOException("Could not remove " + path);
        }
        report.AppendLine($"Removed {remove.Length} assets, {bytes / 1048576.0:F1} MiB (excluding terrain data savings).");
        File.WriteAllText("Logs/terrain-cleanup-result.txt", report.ToString());
        Debug.Log(report.ToString());
    }
}
