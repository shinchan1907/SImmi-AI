const {
    default: makeWASocket,
    useMultiFileAuthState,
    DisconnectReason,
    fetchLatestBaileysVersion,
    makeCacheableSignalKeyStore,
} = require("@whiskeysockets/baileys");
const pino = require("pino");
const { Boom } = require("@hapi/boom");
const qrcode = require("qrcode-terminal");
const axios = require("axios");
const express = require("express");
const fs = require("fs");
const path = require("path");

const logger = pino({ level: "info" });
const app = express();
app.use(express.json());

const PORT = 3000;
const PYTHON_BACKEND_URL = "http://localhost:8001/whatsapp/webhook";

let sock;

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState("auth_info_baileys");
    const { version, isLatest } = await fetchLatestBaileysVersion();
    console.log(`using WA v${version.join(".")}, isLatest: ${isLatest}`);

    sock = makeWASocket({
        version,
        logger,
        printQRInTerminal: true,
        auth: {
            creds: state.creds,
            keys: makeCacheableSignalKeyStore(state.keys, logger),
        },
        generateHighQualityLinkPreview: true,
    });

    sock.ev.on("connection.update", (update) => {
        const { connection, lastDisconnect, qr } = update;
        if (qr) {
            qrcode.generate(qr, { small: true });
        }
        if (connection === "close") {
            const shouldReconnect = (lastDisconnect.error instanceof Boom) ? 
                lastDisconnect.error.output.statusCode !== DisconnectReason.loggedOut : true;
            console.log("connection closed due to ", lastDisconnect.error, ", reconnecting ", shouldReconnect);
            if (shouldReconnect) {
                connectToWhatsApp();
            }
        } else if (connection === "open") {
            console.log("opened connection");
        }
    });

    sock.ev.on("creds.update", saveCreds);

    sock.ev.on("messages.upsert", async (m) => {
        if (m.type === "notify") {
            for (const msg of m.messages) {
                if (!msg.key.fromMe && msg.message) {
                    const from = msg.key.remoteJid;
                    const text = msg.message.conversation || 
                                 msg.message.extendedTextMessage?.text || 
                                 msg.message.imageMessage?.caption ||
                                 "";
                    
                    if (text) {
                        console.log(`Received message from ${from}: ${text}`);
                        try {
                            await axios.post(PYTHON_BACKEND_URL, {
                                from: from,
                                text: text,
                                pushName: msg.pushName || "Unknown"
                            });
                        } catch (err) {
                            console.error("Error sending message to Python backend:", err.message);
                        }
                    }
                }
            }
        }
    });
}

// API for Python to send messages
app.post("/send", async (req, res) => {
    const { to, text } = req.body;
    if (!sock || !to || !text) {
        return res.status(400).json({ error: "Missing parameters or socket not ready" });
    }

    try {
        await sock.sendMessage(to, { text: text });
        res.json({ status: "success" });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.listen(PORT, () => {
    console.log(`Baileys Bridge listening on port ${PORT}`);
    connectToWhatsApp();
});
