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

    private val handler = Handler(Looper.getMainLooper())
    private val reconnectDelayMs = 3000L
    private var isConnecting = false

    // ───────── Lifecycle ─────────

    @RequiresApi(Build.VERSION_CODES.O)
    override fun onCreate() {
        super.onCreate()
        startForeground(1, createNotification("Starting…"))
        connectWebSocket()
    }

    @RequiresApi(Build.VERSION_CODES.O)
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == "LOCK_PC") {
            sendLockCommand()
        }
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    // ───────── WebSocket ─────────

    private fun connectWebSocket() {
        if (isConnecting) return
        isConnecting = true

        val request = Request.Builder()
            .url("ws://172.20.10.2:12345")
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
                updateNotification("Disconnected — retrying…")
                broadcastStatus("Disconnected — retrying…")
                scheduleReconnect()
            }
        })
    }

    private fun scheduleReconnect() {
        handler.postDelayed({ connectWebSocket() }, reconnectDelayMs)
    }

    // ───────── Message handling (OLD BEHAVIOUR) ─────────

    private fun handleMessage(message: String) {
        try {
            val json = JSONObject(message)
            if (json.optString("type") != "STATE") return

            val payload = json.getJSONObject("payload")

            // status — just show *something* so UI moves on
            if (payload.getBoolean("threat")) {
                broadcastStatus("⚠️ INTRUDER DETECTED")
                updateNotification("⚠️ INTRUDER DETECTED")
            } else {
                broadcastStatus("Connected")
            }

            // image — spam display like before
            if (!payload.isNull("image")) {
                val base64 = payload.getString("image")
                showImage(base64)
            }

        } catch (_: Exception) {
            // ignore malformed frames like before
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
