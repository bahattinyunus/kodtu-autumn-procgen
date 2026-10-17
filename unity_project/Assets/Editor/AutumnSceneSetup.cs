using AutumnProcGen.World;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace AutumnProcGen.Editor
{
    public static class AutumnSceneSetup
    {
        [MenuItem("Tools/KODTÜ Autumn/1. Setup Game Scene (Hazır Sahneyi Kur)")]
        public static void SetupGameScene()
        {
            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);
            
            // Delete directional light if present
            var lights = Object.FindObjectsByType<Light>(FindObjectsSortMode.None);
            foreach (var l in lights)
            {
                Object.DestroyImmediate(l.gameObject);
            }

            // Create Autumn World Manager
            GameObject managerObj = new GameObject("AutumnWorldManager", typeof(AutumnWorldManager));
            managerObj.transform.position = Vector3.zero;

            string scenePath = "Assets/Scenes/AutumnWorldScene.unity";
            EditorSceneManager.SaveScene(scene, scenePath);
            AssetDatabase.SaveAssets();

            // Add to build settings
            var buildScenes = new EditorBuildSettingsScene[]
            {
                new EditorBuildSettingsScene(scenePath, true)
            };
            EditorBuildSettings.scenes = buildScenes;

            Debug.Log("<color=#F5D67B><b>[KODTÜ Autumn]</b> Sahne başarıyla kuruldu: " + scenePath + "</color>");
            EditorUtility.DisplayDialog("KODTÜ Autumn ProcGen", "Sahne basariyla kuruldu!\n\nArtik 'Play' (Oynat) butonuna basarak ODTU Sonbahar dunyasinda dolasabilirsiniz.", "Harika!");
        }

        [MenuItem("Tools/KODTÜ Autumn/2. Re-import All Sprites as Pixel Perfect (Pikselleri Yenile)")]
        public static void ReimportSprites()
        {
            string[] guids = AssetDatabase.FindAssets("t:Texture2D", new string[] { "Assets/Sprites", "Assets/Resources/Sprites" });
            foreach (string guid in guids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                TextureImporter importer = AssetImporter.GetAtPath(path) as TextureImporter;
                if (importer != null)
                {
                    importer.textureType = TextureImporterType.Sprite;
                    importer.spritePixelsPerUnit = 16;
                    importer.filterMode = FilterMode.Point;
                    importer.textureCompression = TextureImporterCompression.Uncompressed;
                    importer.mipmapEnabled = false;
                    AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate);
                }
            }
            Debug.Log("<color=#F5D67B><b>[KODTÜ Autumn]</b> Tum pikseller 16 PPU ve Point Filter ile yenilendi!</color>");
        }
    }
}
