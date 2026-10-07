using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

[InitializeOnLoad]
internal static class TerrainRenderDiagnostics
{
    static double next;
    static bool captured;
    static TerrainRenderDiagnostics() { EditorApplication.update += Update; }
    static void Update()
    {
        if (EditorApplication.timeSinceStartup < next || EditorApplication.isCompiling) return;
        next = EditorApplication.timeSinceStartup + 10;
        if (SceneManager.GetActiveScene().name != "TerrainDemoScene") return;
        var s = new StringBuilder();
        s.AppendLine($"{System.DateTime.Now:o} play={EditorApplication.isPlaying} pipeline={GraphicsSettings.currentRenderPipeline}");
        s.AppendLine($"sky={RenderSettings.skybox} sun={RenderSettings.sun} ambient={RenderSettings.ambientMode} {RenderSettings.ambientLight}");
        if (RenderSettings.skybox != null) s.AppendLine(EditorJsonUtility.ToJson(RenderSettings.skybox));
        foreach (var root in SceneManager.GetActiveScene().GetRootGameObjects())
        {
            s.AppendLine($"ROOT {root.name} active={root.activeSelf}");
            foreach (var b in root.GetComponentsInChildren<MonoBehaviour>(true))
            {
                if (b == null || !b.isActiveAndEnabled) continue;
                if (root.name == "UI" || root.name == "Volumes" || root.name == "HDRP Compositor" || b.GetComponent<Camera>() != null)
                    s.AppendLine($"BEHAVIOUR {PathOf(b.transform)} {b.GetType().FullName} {EditorJsonUtility.ToJson(b)}");
            }
            foreach (var c in root.GetComponentsInChildren<Camera>(true))
                s.AppendLine($"CAM {PathOf(c.transform)} active={c.isActiveAndEnabled} pos={c.transform.position} scale={c.transform.lossyScale} clear={c.clearFlags} bg={c.backgroundColor} mask={c.cullingMask} clip={c.nearClipPlane}/{c.farClipPlane} rect={c.rect} target={c.targetTexture} stereo={c.stereoEnabled}");
            foreach (var l in root.GetComponentsInChildren<Light>(true))
                s.AppendLine($"LIGHT {PathOf(l.transform)} active={l.isActiveAndEnabled} intensity={l.intensity} type={l.type} bake={l.lightmapBakeType} forward={l.transform.forward}");
            foreach (var c in root.GetComponentsInChildren<Canvas>(true))
                s.AppendLine($"CANVAS {PathOf(c.transform)} active={c.isActiveAndEnabled} mode={c.renderMode}");
            foreach (var t in root.GetComponentsInChildren<Terrain>(true))
                s.AppendLine($"TERRAIN {t.name} active={t.isActiveAndEnabled} draw={t.drawHeightmap} pos={t.transform.position}");
        }
        Directory.CreateDirectory("Logs");
        File.WriteAllText("Logs/terrain-render-state.txt", s.ToString());
        if (!captured && Camera.main != null)
        {
            captured = true;
            var source = Camera.main;
            var go = new GameObject("Temporary render diagnostic", typeof(Camera));
            go.hideFlags = HideFlags.HideAndDontSave;
            var camera = go.GetComponent<Camera>();
            camera.CopyFrom(source);
            camera.enabled = false;
            camera.stereoTargetEye = StereoTargetEyeMask.None;
            go.transform.SetPositionAndRotation(source.transform.position, source.transform.rotation);
            var rt = new RenderTexture(640, 480, 24);
            var previous = RenderTexture.active;
            var texture = new Texture2D(640, 480, TextureFormat.RGB24, false);
            try
            {
                camera.targetTexture = rt;
                camera.Render();
                RenderTexture.active = rt;
                texture.ReadPixels(new Rect(0, 0, 640, 480), 0, 0);
                texture.Apply();
                File.WriteAllBytes("Logs/terrain-camera-diagnostic.png", texture.EncodeToPNG());
            }
            finally
            {
                RenderTexture.active = previous;
                Object.DestroyImmediate(go);
                Object.DestroyImmediate(rt);
                Object.DestroyImmediate(texture);
            }
        }
    }
    static string PathOf(Transform t) { return t.parent == null ? t.name : PathOf(t.parent) + "/" + t.name; }
}
