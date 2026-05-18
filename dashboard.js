const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const fs = require('fs');
const path = require('path');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.static(path.join(__dirname, 'public')));

const server = http.createServer(app);
const io = new Server(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

const LOG_FILE = path.join(__dirname, 'logs', 'bot.log');
const STATE_FILE = path.join(__dirname, 'logs', 'dashboard_state.json');

// อ่านสถานะล่าสุดถ้ามี
let botState = {
    balance: 0,
    price: 0,
    rsi: 0,
    position: 'None',
    logs: [],
    initialBalance: null,
    dailyStartBalance: null,
    lastDate: null
};

if (fs.existsSync(STATE_FILE)) {
    try {
        botState = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
    } catch (e) {
        console.error("Error reading state:", e);
    }
}

// Endpoint หน้าเว็บหลัก
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Endpoint รับข้อมูลอัปเดตจาก Python Bot
app.use(express.json());
app.post('/api/update', (req, res) => {
    const data = req.body;
    
    // อัปเดต State
    if (data.type === 'status') {
        const today = new Date().toDateString();
        
        // ตั้งค่าวันแรกที่เริ่มรัน
        if (!botState.initialBalance && data.balance > 0) {
            botState.initialBalance = data.balance;
            botState.dailyStartBalance = data.balance;
            botState.lastDate = today;
        } 
        // รีเซ็ตยอดประจำวันเมื่อเปลี่ยนวัน
        else if (botState.lastDate && botState.lastDate !== today) {
            botState.dailyStartBalance = botState.balance;
            botState.lastDate = today;
        }

        botState.balance = data.balance;
        botState.price = data.price;
        botState.rsi = data.rsi;
        botState.position = data.position;
        
        // คำนวณ P&L
        botState.lifetimePnL = (botState.balance - botState.initialBalance) || 0;
        botState.dailyPnL = (botState.balance - botState.dailyStartBalance) || 0;
        botState.lifetimePnLPct = botState.initialBalance ? (botState.lifetimePnL / botState.initialBalance) * 100 : 0;
        botState.dailyPnLPct = botState.dailyStartBalance ? (botState.dailyPnL / botState.dailyStartBalance) * 100 : 0;

        io.emit('statusUpdate', botState);
    } 
    else if (data.type === 'log') {
        const newLog = data.message;
        
        // แน่ใจว่า botState.logs เป็น array
        if (!Array.isArray(botState.logs)) botState.logs = [];
        
        botState.logs.push(newLog);
        if (botState.logs.length > 100) botState.logs.shift(); // เก็บไว้แค่ 100 บรรทัด
        io.emit('newLog', newLog);
    }

    // บันทึก State ลงไฟล์
    fs.writeFileSync(STATE_FILE, JSON.stringify(botState));
    
    res.json({ success: true });
});

io.on('connection', (socket) => {
    socket.emit('statusUpdate', botState);
    if (botState.logs && botState.logs.length > 0) {
        socket.emit('initLogs', botState.logs);
    }
});

const PORT = 3000;
server.listen(PORT, () => {
    console.log(`✅ Dashboard Server running on http://localhost:${PORT}`);
});
