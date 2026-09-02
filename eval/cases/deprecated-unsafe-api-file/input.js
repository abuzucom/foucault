function buildFrame(header, payloadLength) {
  // eslint-disable-next-line node/no-deprecated-api
  const frame = new Buffer(payloadLength + header.length);
  header.copy(frame, 0);
  return frame;
}

module.exports = { buildFrame };
