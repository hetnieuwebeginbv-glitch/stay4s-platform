package com.stay4s.companion

import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import okhttp3.*
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

class MessagesActivity : AppCompatActivity() {
    
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()
    
    private var userId = ""
    private var userName = ""
    private var currentContactId = ""
    private var currentContactName = ""
    private val messages = mutableListOf<Msg>()
    private lateinit var adapter: MsgAdapter
    
    // API URLs
    private val apiUrl = "https://companion.stay4s.com"
    private val fallbackUrl = "http://100.123.235.81:8200"
    private var useFallback = false
    
    data class Msg(val content: String, val isMine: Boolean, val isAi: Boolean = false)
    data class Contact(val id: String, val name: String, val avatar: String)
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Load saved user
        val prefs = getSharedPreferences("stay4s", MODE_PRIVATE)
        userId = prefs.getString("uid", "") ?: ""
        userName = prefs.getString("name", "") ?: ""
        
        if (userId.isEmpty()) {
            showLoginScreen()
        } else {
            showContactsScreen()
        }
    }
    
    fun showLoginScreen() {
        setContentView(R.layout.activity_login)
        
        val btnRegister = findViewById<Button>(R.id.btnRegister)
        val btnLogin = findViewById<Button>(R.id.btnLogin)
        val etName = findViewById<EditText>(R.id.etName)
        val etPhone = findViewById<EditText>(R.id.etPhone)
        val etPassword = findViewById<EditText>(R.id.etPassword)
        
        btnRegister.setOnClickListener {
            val name = etName.text.toString()
            val phone = etPhone.text.toString()
            val pw = etPassword.text.toString()
            if (name.isNotEmpty() && phone.isNotEmpty() && pw.isNotEmpty()) {
                apiCall("/api/register", """{"name":"$name","phone":"$phone","password":"$pw"}""") { resp ->
                    if (resp.has("user_id")) {
                        userId = resp.getString("user_id")
                        userName = name
                        saveUser()
                        runOnUiThread { showContactsScreen() }
                    } else {
                        runOnUiThread { Toast.makeText(this, resp.optString("error", "Fout"), Toast.LENGTH_SHORT).show() }
                    }
                }
            }
        }
        
        btnLogin.setOnClickListener {
            val phone = etPhone.text.toString()
            val pw = etPassword.text.toString()
            apiCall("/api/login", """{"phone":"$phone","password":"$pw"}""") { resp ->
                if (resp.has("user_id")) {
                    userId = resp.getString("user_id")
                    userName = resp.getString("name")
                    saveUser()
                    runOnUiThread { showContactsScreen() }
                } else {
                    runOnUiThread { Toast.makeText(this, resp.optString("error", "Fout"), Toast.LENGTH_SHORT).show() }
                }
            }
        }
    }
    
    fun showContactsScreen() {
        setContentView(R.layout.activity_contacts)
        findViewById<TextView>(R.id.tvUserName).text = "Welkom, $userName"
        
        val rvContacts = findViewById<RecyclerView>(R.id.rvContacts)
        rvContacts.layoutManager = LinearLayoutManager(this)
        
        // Load contacts
        apiCall("/api/contacts/$userId", null) { resp ->
            val contacts = mutableListOf<Contact>()
            contacts.add(Contact("stay4s-ai", "Stay4S AI", "AI"))
            if (resp.has("contacts")) {
                val arr = resp.getJSONArray("contacts")
                for (i in 0 until arr.length()) {
                    val c = arr.getJSONObject(i)
                    contacts.add(Contact(c.getString("id"), c.getString("name"), c.optString("avatar", "S4")))
                }
            }
            runOnUiThread {
                val contactAdapter = ContactAdapter(contacts) { contact ->
                    openChat(contact.id, contact.name)
                }
                rvContacts.adapter = contactAdapter
            }
        }
        
        findViewById<Button>(R.id.btnAddContact).setOnClickListener {
            val phone = "0612345678" // Simplified - in production show a dialog
            apiCall("/api/search", """{"phone":"$phone"}""") { resp ->
                if (resp.has("user_id")) {
                    val cid = resp.getString("user_id")
                    apiCall("/api/contacts/add", """{"user_id":"$userId","contact_id":"$cid"}""") { _ ->
                        runOnUiThread { showContactsScreen() }
                    }
                }
            }
        }
    }
    
    fun openChat(contactId: String, contactName: String) {
        currentContactId = contactId
        currentContactName = contactName
        setContentView(R.layout.activity_chat)
        findViewById<TextView>(R.id.tvChatName).text = contactName
        
        val rvMessages = findViewById<RecyclerView>(R.id.rvMessages)
        rvMessages.layoutManager = LinearLayoutManager(this)
        adapter = MsgAdapter(messages)
        rvMessages.adapter = adapter
        
        // Load message history
        apiCall("/api/messages/$userId/$contactId", null) { resp ->
            messages.clear()
            if (resp.has("messages")) {
                val arr = resp.getJSONArray("messages")
                for (i in 0 until arr.length()) {
                    val m = arr.getJSONObject(i)
                    messages.add(Msg(m.getString("content"), m.getString("sender") == userId, m.optBoolean("is_ai", false)))
                }
            }
            runOnUiThread { adapter.notifyDataSetChanged() }
        }
        
        // Send button
        val etInput = findViewById<EditText>(R.id.etMessage)
        findViewById<Button>(R.id.btnSend).setOnClickListener {
            val text = etInput.text.toString().trim()
            if (text.isNotEmpty()) {
                etInput.text.clear()
                messages.add(Msg(text, true))
                adapter.notifyItemInserted(messages.size - 1)
                
                apiCall("/api/send", """{"sender_id":"$userId","receiver_id":"$contactId","content":"$text"}""") { resp ->
                    if (resp.has("ai_response")) {
                        val aiResp = resp.getString("ai_response")
                        runOnUiThread {
                            messages.add(Msg(aiResp, false, true))
                            adapter.notifyItemInserted(messages.size - 1)
                        }
                    }
                }
            }
        }
    }
    
    fun apiCall(endpoint: String, body: String?, callback: (JSONObject) -> Unit) {
        val url = (if (useFallback) fallbackUrl else apiUrl) + endpoint
        val builder = Request.Builder().url(url)
        if (body != null) {
            builder.post(RequestBody.create(MediaType.parse("application/json"), body))
        }
        
        client.newCall(builder.build()).enqueue(object : Callback {
            override fun onResponse(call: Call, response: Response) {
                try {
                    val respStr = response.body()?.string() ?: "{}"
                    callback(JSONObject(respStr))
                } catch (e: Exception) {
                    if (!useFallback) {
                        useFallback = true
                        apiCall(endpoint, body, callback)
                    } else {
                        callback(JSONObject("""{"error":"Verbinding mislukt"}"""))
                    }
                }
            }
            override fun onFailure(call: Call, e: IOException) {
                if (!useFallback) {
                    useFallback = true
                    apiCall(endpoint, body, callback)
                } else {
                    runOnUiThread { Toast.makeText(this@MessagesActivity, "Geen verbinding", Toast.LENGTH_SHORT).show() }
                }
            }
        })
    }
    
    fun saveUser() {
        getSharedPreferences("stay4s", MODE_PRIVATE).edit()
            .putString("uid", userId)
            .putString("name", userName)
            .apply()
    }
    
    // Adapters
    inner class MsgAdapter(val msgs: List<Msg>) : RecyclerView.Adapter<MsgAdapter.MsgVH>() {
        inner class MsgVH(v: View) : RecyclerView.ViewHolder(v) {
            val tvMsg: TextView = v.findViewById(R.id.tvMsg)
        }
        override fun onCreateViewHolder(parent: android.view.ViewGroup, type: Int): MsgVH {
            val view = layoutInflater.inflate(R.layout.item_message, parent, false)
            return MsgVH(view)
        }
        override fun onBindViewHolder(h: MsgVH, pos: Int) {
            val m = msgs[pos]
            h.tvMsg.text = m.content
            val params = h.tvMsg.layoutParams as RecyclerView.LayoutParams
            if (m.isMine) {
                h.tvMsg.setBackgroundResource(R.drawable.bg_msg_sent)
                params.gravity = android.view.Gravity.END
            } else if (m.isAi) {
                h.tvMsg.setBackgroundResource(R.drawable.bg_msg_ai)
                params.gravity = android.view.Gravity.START
            } else {
                h.tvMsg.setBackgroundResource(R.drawable.bg_msg_received)
                params.gravity = android.view.Gravity.START
            }
            h.tvMsg.layoutParams = params
        }
        override fun getItemCount() = msgs.size
    }
    
    inner class ContactAdapter(val contacts: List<Contact>, val onClick: (Contact) -> Unit) : RecyclerView.Adapter<ContactAdapter.ContactVH>() {
        inner class ContactVH(v: View) : RecyclerView.ViewHolder(v) {
            val tvName: TextView = v.findViewById(R.id.tvContactName)
            val tvAvatar: TextView = v.findViewById(R.id.tvAvatar)
        }
        override fun onCreateViewHolder(parent: android.view.ViewGroup, type: Int): ContactVH {
            val view = layoutInflater.inflate(R.layout.item_contact, parent, false)
            return ContactVH(view)
        }
        override fun onBindViewHolder(h: ContactVH, pos: Int) {
            val c = contacts[pos]
            h.tvName.text = c.name
            h.tvAvatar.text = c.avatar
            h.itemView.setOnClickListener { onClick(c) }
        }
        override fun getItemCount() = contacts.size
    }
}