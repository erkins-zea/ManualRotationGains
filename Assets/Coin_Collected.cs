using UnityEngine;

public class Coin_Collected : MonoBehaviour
{
    void OnTriggerEnter (Collider other)
    {
        Destroy(gameObject);
        //PlaySFX(coinCollect); 
        // <- establish audio manager so there can be coin collect sound effects
    }
}
