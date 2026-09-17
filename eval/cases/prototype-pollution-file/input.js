function deepMerge(target, source) {
  for (const key of Object.keys(source)) {
    if (typeof source[key] === "object" && source[key] !== null) {
      target[key] = deepMerge(target[key] || {}, source[key]);
    } else {
      target[key] = source[key];
    }
  }
  return target;
}

app.post("/api/preferences", (req, res) => {
  const prefs = deepMerge({}, req.body);
  savePreferences(req.user.id, prefs);
  res.json({ ok: true });
});
