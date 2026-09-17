const WebSocket = require("ws");
const chat = require("./chat");

const wss = new WebSocket.Server({ port: 8080 });

wss.on("connection", (socket, req) => {
  const user = chat.userFromCookie(req.headers.cookie);
  if (!user) {
    socket.close();
    return;
  }
  socket.on("message", (raw) => {
    const msg = JSON.parse(raw);
    if (msg.type === "history") {
      socket.send(JSON.stringify(chat.historyFor(msg.channelId)));
    }
  });
});
