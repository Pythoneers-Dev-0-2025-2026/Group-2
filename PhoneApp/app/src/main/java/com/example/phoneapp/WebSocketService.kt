package com.example.phoneapp

import android.app.*
import android.content.Intent
import android.os.*
import androidx.annotation.RequiresApi
import okhttp3.*
import org.json.JSONObject
import android.util.Base64

class WebSocketService : Service() {

    private lateinit var webSocket: WebSocket
    private val client = OkHttpClient()

    private var isConnecting = false
    private var ipAddress: String? = null

    // ───────── Lifecycle ─────────

    @RequiresApi(Build.VERSION_CODES.O)
    override fun onCreate() {
        super.onCreate()
        startForeground(1, createNotification("Starting…"))
    }

    @RequiresApi(Build.VERSION_CODES.O)
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "LOCK_PC") {
            sendLockCommand()
        } else {
            ipAddress = intent?.getStringExtra("ipAddress")
            connectWebSocket()
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        if (::webSocket.isInitialized) {
            webSocket.close(1000, "Service destroyed")
        }
    }

    // ───────── WebSocket ─────────

    private fun connectWebSocket() {
        if (isConnecting || ipAddress == null) return
        isConnecting = true
        broadcastStatus("Connecting to $ipAddress…")
        updateNotification("Connecting to $ipAddress…")

        val request = Request.Builder()
            .url("ws://$ipAddress:12345")
            .build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {

            @RequiresApi(Build.VERSION_CODES.O)
            override fun onOpen(ws: WebSocket, response: Response) {
                isConnecting = false
                updateNotification("Connected")
                broadcastStatus("Connected")
            }

            override fun onMessage(ws: WebSocket, text: String) {
                handleMessage(text)
            }

            @RequiresApi(Build.VERSION_CODES.O)
            override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                isConnecting = false
                updateNotification("Connection Failed")
                broadcastStatus("Connection Failed")
                sendBroadcast(
                    Intent("WS_CONNECTION_FAILURE").apply {
                        setPackage(packageName)
                    }
                )
                stopSelf()
            }
        })
    }

    // ───────── Message handling ─────────

    private fun handleMessage(message: String) {
        try {
            val json = JSONObject(message)
            if (json.optString("type") != "STATE") return

            val payload = json.getJSONObject("payload")

            if (payload.getBoolean("threat")) {
                broadcastStatus("⚠️ INTRUDER DETECTED")
                updateNotification("⚠️ INTRUDER DETECTED")
            } else {
                broadcastStatus("Connected")
            }

            if (!payload.isNull("image")) {
                val base64 = payload.getString("image")
                showImage(base64)
            } else {
                 sendBroadcast(
                    Intent("WS_IMAGE").apply {
                        putExtra("hasImage", false)
                        setPackage(packageName)
                    }
                )
            }

        } catch (_: Exception) {
            // Ignore malformed frames
        }
    }

    // ───────── Commands ─────────

    private fun sendLockCommand() {
        if (!::webSocket.isInitialized) return

        val msg = JSONObject().apply {
            put("type", "COMMAND")
            put("payload", JSONObject().apply {
                put("action", "LOCK")
            })
        }

        webSocket.send(msg.toString())
        broadcastStatus("Lock command sent")
    }

    // ───────── Broadcast helpers ─────────

    private fun broadcastStatus(status: String) {
        sendBroadcast(
            Intent("WS_STATUS").apply {
                putExtra("status", status)
                setPackage(packageName)
            }
        )
    }

    private fun showImage(base64: String) {
        try {
            val bytes = Base64.decode(base64, Base64.DEFAULT)
            sendBroadcast(
                Intent("WS_IMAGE").apply {
                    putExtra("hasImage", true)
                    putExtra("imageBytes", bytes)
                    setPackage(packageName)
                }
            )
        } catch (_: Exception) {
            // ignore bad image, keep last one
        }
    }

    // ───────── Notification ─────────

    @RequiresApi(Build.VERSION_CODES.O)
    private fun createNotification(text: String): Notification {
        val channelId = "ws_channel"

        val channel = NotificationChannel(
            channelId,
            "WebSocket Service",
            NotificationManager.IMPORTANCE_LOW
        )
        getSystemService(NotificationManager::class.java)
            .createNotificationChannel(channel)

        return Notification.Builder(this, channelId)
            .setContentTitle("PC Lock Monitor")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .build()
    }

    @RequiresApi(Build.VERSION_CODES.O)
    private fun updateNotification(text: String) {
        getSystemService(NotificationManager::class.java)
            .notify(1, createNotification(text))
    }
}
