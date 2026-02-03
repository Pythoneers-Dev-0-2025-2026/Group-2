package com.example.phoneapp

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import androidx.appcompat.app.AppCompatActivity

class IpEntryActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_ip_entry)

        val ipAddressInput = findViewById<EditText>(R.id.ipAddressInput)
        val connectButton = findViewById<Button>(R.id.connectButton)

        connectButton.setOnClickListener {
            val ipAddress = ipAddressInput.text.toString()
            if (ipAddress.isNotEmpty()) {
                val intent = Intent(this, MainActivity::class.java).apply {
                    putExtra("ipAddress", ipAddress)
                }
                startActivity(intent)
                finish()
            }
        }
    }
}
