package com.example.phoneapp

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.BitmapFactory
import android.os.Build
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import android.widget.Toast
import androidx.annotation.RequiresApi
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {

    private lateinit var statusText: TextView
    private lateinit var imageView: ImageView
    private lateinit var lockButton: Button

    // ───────── Status receiver ─────────
    private val statusReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val status = intent.getStringExtra("status") ?: return
            statusText.text = status
        }
    }

    // ───────── Image receiver ─────────
    private val imageReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val hasImage = intent.getBooleanExtra("hasImage", false)

            if (!hasImage) {
                imageView.visibility = View.GONE
                lockButton.visibility = View.GONE
                return
            }

            val bytes = intent.getByteArrayExtra("imageBytes") ?: return
            val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            imageView.setImageBitmap(bitmap)
            imageView.visibility = View.VISIBLE
            lockButton.visibility = View.VISIBLE
        }
    }

    // ───────── Connection failure receiver ─────────
    private val connectionFailureReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            Toast.makeText(context, "Connection Failed. Please re-enter the IP Address.", Toast.LENGTH_LONG).show()
            val ipEntryIntent = Intent(context, IpEntryActivity::class.java)
            startActivity(ipEntryIntent)
            finish()
        }
    }

    @RequiresApi(Build.VERSION_CODES.O)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        statusText = findViewById(R.id.statusText)
        imageView = findViewById(R.id.imageView)
        lockButton = findViewById(R.id.lockButton)

        lockButton.setOnClickListener {
            val intent = Intent(this, WebSocketService::class.java).apply {
                action = "LOCK_PC"
            }
            ContextCompat.startForegroundService(this, intent)
        }

        // Start WebSocket service
        val ipAddress = intent.getStringExtra("ipAddress")
        val serviceIntent = Intent(this, WebSocketService::class.java).apply {
            putExtra("ipAddress", ipAddress)
        }
        ContextCompat.startForegroundService(this, serviceIntent)

        // Register receivers
        registerReceiver(
            statusReceiver,
            IntentFilter("WS_STATUS"),
            RECEIVER_NOT_EXPORTED
        )

        registerReceiver(
            imageReceiver,
            IntentFilter("WS_IMAGE"),
            RECEIVER_NOT_EXPORTED
        )

        registerReceiver(
            connectionFailureReceiver,
            IntentFilter("WS_CONNECTION_FAILURE"),
            RECEIVER_NOT_EXPORTED
        )
    }

    override fun onDestroy() {
        super.onDestroy()
        unregisterReceiver(statusReceiver)
        unregisterReceiver(imageReceiver)
        unregisterReceiver(connectionFailureReceiver)
    }
}
