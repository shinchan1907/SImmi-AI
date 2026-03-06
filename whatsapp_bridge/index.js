const {
    default: makeWASocket,
    useMultiFileAuthState,
    DisconnectReason,
    fetchLatestBaileysVersion,
    makeCacheableSignalKeyStore,
    downloadMediaMessage
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
const PYTHON_BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8001/whatsapp/webhook";
const TEMP_DIR = path.join(__dirname, "temp_media");

if (!fs.existsSync(TEMP_DIR)) {
    fs.mkdirSync(TEMP_DIR, { recursive: true });
}

let sock;
let status = {
    connected: false,
    number: null,
    msg_count: 0,
    start_time: Date.now()
};

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
            status.connected = false;
            const shouldReconnect = (lastDisconnect.error instanceof Boom) ?
                lastDisconnect.error.output.statusCode !== DisconnectReason.loggedOut : true;
            console.log("connection closed due to ", lastDisconnect.error, ", reconnecting ", shouldReconnect);
            if (shouldReconnect) {
                connectToWhatsApp();
            }
        } else if (connection === "open") {
            status.connected = true;
            status.number = sock.user.id.split(":")[0];
            console.log("opened connection");
        }
    });

    sock.ev.on("creds.update", saveCreds);

    sock.ev.on("messages.upsert", async (m) => {
        if (m.type === "notify") {
            for (const msg of m.messages) {
                if (!msg.key.fromMe && msg.message) {
                    status.msg_count++;
                    const from = msg.key.remoteJid;
                    const type = Object.keys(msg.message)[0];

                    let payload = {
                        from: from,
                        pushName: msg.pushName || "Unknown",
                        timestamp: msg.messageTimestamp,
                        type: type
                    };

                    // Handle text
                    if (type === "conversation" || type === "extendedTextMessage") {
                        payload.text = msg.message.conversation || msg.message.extendedTextMessage?.text;
                    }
                    // Handle Audio (Voice Notes)
                    else if (type === "audioMessage") {
                        console.log("Received audio message, downloading...");
                        try {
                            const buffer = await downloadMediaMessage(msg, 'buffer', {}, { logger, reuploadRequest: sock.updateMediaMessage });
                            const fileName = `audio_${Date.now()}.ogg`;
                            const filePath = path.join(TEMP_DIR, fileName);
                            fs.writeFileSync(filePath, buffer);
                            payload.audio_path = filePath;
                            payload.is_voice = msg.message.audioMessage.ptt === true;
                        } catch (err) {
                            console.error("Failed to download audio:", err);
                        }
                    }

                    if (payload.text || payload.audio_path) {
                        console.log(`Forwarding ${type} from ${from} to Backend...`);
                        try {
                            await axios.post(PYTHON_BACKEND_URL, payload);
                        } catch (err) {
                            console.error("Error sending to Python backend:", err.message);
                        }
                    }
                }
            }
        }
    });
}

// API for Python to send messages
app.post("/send", async (req, res) => {
    const { to, text, audio_path, is_voice } = req.body;
    if (!sock || !to) {
        return res.status(400).json({ error: "Missing parameters or socket not ready" });
    }

    try {
        if (audio_path && fs.existsSync(audio_path)) {
            const buffer = fs.readFileSync(audio_path);
            await sock.sendMessage(to, {
                audio: buffer,
                mimetype: 'audio/mp4',
                ptt: is_voice || false
            });
        } else if (text) {
            await sock.sendMessage(to, { text: text });
        }
        res.json({ status: "success" });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

// Status endpoint for CLI
app.get("/status", (req, res) => {
    res.json({
        ...status,
        uptime: Math.floor((Date.now() - status.start_time) / 1000) + "s"
    });
});

app.listen(PORT, "0.0.0.0", () => {
    console.log(`Baileys Bridge listening on port ${PORT}`);
    connectToWhatsApp();
});
