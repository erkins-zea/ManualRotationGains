using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

// Also runs after script reload so conversion problems are visible in the Console.
[InitializeOnLoad]
internal static class TerrainMaterialValidation
{
    private const string Folder = "Assets/TerrainDemoScene_HDRP";

    static TerrainMaterialValidation()
    {
        EditorApplication.delayCall += ValidateWhenReady;
    }

    private static void ValidateWhenReady()
    {
        if (EditorApplication.isCompiling || EditorApplication.isUpdating)
        {
            EditorApplication.delayCall += ValidateWhenReady;
            return;
        }
        Validate();
    }

    [MenuItem("Tools/Terrain Environment/Validate URP Materials")]
    private static void Validate()
    {
        if (!AssetDatabase.IsValidFolder(Folder))
            return;

        var report = new StringBuilder();
        int count = 0, errors = 0;
        var pipeline = GraphicsSettings.currentRenderPipeline;
        report.AppendLine("Render pipeline: " + (pipeline == null ? "Built-in" : pipeline.GetType().Name));
        if (pipeline == null || pipeline.GetType().Name != "UniversalRenderPipelineAsset")
            errors++;

        foreach (var guid in AssetDatabase.FindAssets("t:Material", new[] { Folder }))
        {
            var path = AssetDatabase.GUIDToAssetPath(guid);
            // Embedded model materials are not the external materials used by these prefabs.
            if (!path.EndsWith(".mat") && !path.EndsWith(".asset"))
                continue;
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            var shader = material == null ? null : material.shader;
            bool valid = shader != null && shader.isSupported
                && shader.name.StartsWith("Universal Render Pipeline/")
                && !ShaderUtil.ShaderHasError(shader);
            if (valid && shader.name == "Universal Render Pipeline/Lit")
            {
                // Catch latent emission too: the URP inspector can enable its
                // keyword later when a nonblack emission color is retained.
                valid = !material.IsKeywordEnabled("_EMISSION")
                    && material.GetColor("_EmissionColor").maxColorComponent == 0f;
            }
            count++;
            if (!valid) errors++;
            report.AppendLine((valid ? "OK " : "ERROR ") + path + " -> "
                + (shader == null ? "missing shader" : shader.name));
        }
        report.AppendLine($"Materials checked: {count}; errors: {errors}");
        Directory.CreateDirectory("Logs");
        File.WriteAllText("Logs/terrain-urp-validation.txt", report.ToString());
        if (errors > 0)
            Debug.LogError("Terrain URP validation found problems. See Logs/terrain-urp-validation.txt");
        else
            Debug.Log($"Terrain URP validation: {count} materials passed. See Logs/terrain-urp-validation.txt");
    }
}
