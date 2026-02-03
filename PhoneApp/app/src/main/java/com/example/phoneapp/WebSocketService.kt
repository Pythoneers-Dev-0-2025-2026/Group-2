package com.example.phoneapp

import android.app.*
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.annotation.RequiresApi
import okhttp3.*
import org.json.JSONObject

class WebSocketService : Service() {

    private lateinit var webSocket: WebSocket
    private val client = OkHttpClient()

    @RequiresApi(Build.VERSION_CODES.O)
    override fun onCreate() {
        super.onCreate()

        startForeground(1, createNotification("Connecting to PC…"))
        connectWebSocket()
    }

    private fun connectWebSocket() {
        val request = Request.Builder()
            .url("ws://10.75.209.47:12345")
            .build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {

            @RequiresApi(Build.VERSION_CODES.O)
            override fun onOpen(webSocket: WebSocket, response: Response) {
                webSocket.send("""{"from":"android"}""")
                updateNotification("Connected")
                broadcastStatus("Connected")
            }

            @RequiresApi(Build.VERSION_CODES.O)
            override fun onMessage(webSocket: WebSocket, text: String) {
                handleMessage(text)
            }

            @RequiresApi(Build.VERSION_CODES.O)
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                updateNotification("Disconnected: ${t.message}")
                broadcastStatus("Disconnected: ${t.message}")
            }
        })
    }

    @RequiresApi(Build.VERSION_CODES.O)
    private fun handleMessage(message: String) {
        try {
            val json = JSONObject(message)
            val locked = json.getBoolean("lock_status")

            val statusText =
                if (locked) "PC Locked" else "PC Unlocked"

            updateNotification(statusText)
            broadcastStatus(statusText)

        } catch (_: Exception) {
            updateNotification("Bad data from server")
            broadcastStatus("Bad data from server")
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

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
        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(1, createNotification(text))
    }

    private fun broadcastStatus(status: String) {
        val intent = Intent("WS_STATUS")
        intent.putExtra("status", status)
        sendBroadcast(intent)
    }
}
