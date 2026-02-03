package com.example.phoneapp

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.BitmapFactory
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import androidx.annotation.RequiresApi
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {

    private lateinit var statusText: TextView
    private lateinit var imageView: ImageView

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
                imageView.setImageDrawable(null)
                imageView.setBackgroundColor(Color.BLACK)
                return
            }

            val bytes = intent.getByteArrayExtra("imageBytes") ?: return
            val bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            imageView.setBackgroundColor(Color.BLACK)
            imageView.setImageBitmap(bitmap)
        }
    }

    @RequiresApi(Build.VERSION_CODES.O)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        statusText = findViewById(R.id.statusText)
        imageView = findViewById(R.id.imageView)

        val lockButton = findViewById<Button>(R.id.lockButton)
        lockButton.setOnClickListener {
            val intent = Intent(this, WebSocketService::class.java).apply {
                action = "LOCK_PC"
            }
            ContextCompat.startForegroundService(this, intent)
        }

        // Start WebSocket service
        val serviceIntent = Intent(this, WebSocketService::class.java)
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
    }

    override fun onDestroy() {
        super.onDestroy()
        unregisterReceiver(statusReceiver)
        unregisterReceiver(imageReceiver)
    }
}
