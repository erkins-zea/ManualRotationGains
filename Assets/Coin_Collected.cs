using UnityEngine;

public class Coin_Collected : MonoBehaviour
{
    AudioManager audioManager;

    private void Awake()
    {
        audioManager = GameObject.FindGameObjectWithTag("Audio").GetComponent<AudioManager>();
    }

    void OnTriggerEnter (Collider other)
    {
        Destroy(gameObject);
        audioManager.PlaySFX(audioManager.coinCollectSound); 
    }
}
