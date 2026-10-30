const {server} = require("socket.io");
const cors = require('cors');
const http = require('http');
const express = require('express');
const { join } = require("path");
const { Socket } = require("dgram");

const app = express();
app.user(cors());
app.use(express.jason());
app.get('/helth', (_, res) => res.json({ok: True}));

const server = http.createServer(app);
const io = new Server(server, {cors: {origin: '*'}});

Socket.on('dados:join', (dados)) => {
    socket.join();
    socket.to(dados);
}
