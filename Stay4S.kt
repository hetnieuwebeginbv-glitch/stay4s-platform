package nl.stay4s.sdk

import okhttp3.*
import org.json.JSONObject
import org.json.JSONArray

/**
 * Stay4S Kotlin SDK - voor Stay4Companion app
 * Gradle: implementation 'nl.stay4s:sdk:1.0'
 * 
 * Gebruik:
 *   val api = Stay4S("jouw-api-key")
 *   val antwoord = api.chat("Hallo, wie ben jij?")
 *   val scan = api.scan("Bel naar 06-12345678")
 */

class Stay4S(
    private val apiKey: String,
    private val baseUrl: String = "https://api.stay4s.com/v1"
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(30, java.util.concurrent.TimeUnit.SECONDS)
        .readTimeout(120, java.util.concurrent.TimeUnit.SECONDS)
        .build()

    private fun post(endpoint: String, body: JSONObject): JSONObject {
        val request = Request.Builder()
            .url("$baseUrl$endpoint")
            .header("Authorization", "Bearer $apiKey")
            .header("Content-Type", "application/json")
            .post(RequestBody.create(body.toString(), MediaType.parse("application/json")))
            .build()
        client.newCall(request).execute().use { response ->
            val json = JSONObject(response.body()!!.string())
            if (!response.isSuccessful) throw Exception("HTTP ${response.code()}: $json")
            return json
        }
    }

    fun chat(message: String, system: String = "", history: List<JSONObject> = emptyList()): JSONObject {
        val body = JSONObject()
            .put("message", message)
            .put("system", system)
            .put("history", JSONArray(history))
        return post("/chat", body)
    }

    fun scan(text: String): JSONObject {
        return post("/scan", JSONObject().put("text", text))
    }

    fun translate(text: String, source: String = "nl", target: String = "en"): JSONObject {
        return post("/translate", JSONObject()
            .put("text", text)
            .put("source_lang", source)
            .put("target_lang", target))
    }

    fun summarize(text: String, format: String = "bullet"): JSONObject {
        return post("/summarize", JSONObject()
            .put("text", text)
            .put("format", format))
    }

    fun search(query: String, limit: Int = 5): JSONObject {
        return post("/search", JSONObject()
            .put("query", query)
            .put("limit", limit))
    }

    fun code(prompt: String, language: String = "python"): JSONObject {
        return post("/code", JSONObject()
            .put("prompt", prompt)
            .put("language", language))
    }

    fun email(topic: String, tone: String = "formeel", recipient: String = ""): JSONObject {
        return post("/email", JSONObject()
            .put("topic", topic)
            .put("tone", tone)
            .put("recipient", recipient))
    }

    fun content(topic: String, type: String = "blog", length: String = "medium"): JSONObject {
        return post("/content", JSONObject()
            .put("topic", topic)
            .put("type", type)
            .put("length", length))
    }

    fun agents(task: String, agent: String = "default"): JSONObject {
        return post("/agents", JSONObject()
            .put("task", task)
            .put("agent", agent))
    }

    fun health(): JSONObject {
        val request = Request.Builder()
            .url("$baseUrl/health")
            .header("Authorization", "Bearer $apiKey")
            .get()
            .build()
        client.newCall(request).execute().use { response ->
            return JSONObject(response.body()!!.string())
        }
    }
}
