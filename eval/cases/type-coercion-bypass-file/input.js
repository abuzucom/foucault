// Express + Mongoose account routes.

const resetSchema = Joi.object({
  email: Joi.string().email().required(),
  token: Joi.string().required(),
});

async function resetPassword(req, res) {
  const { error, value } = resetSchema.validate(req.body);
  if (error) return res.status(400).json({ error: error.message });

  const user = await User.findOne({ email: value.email, resetToken: value.token });
  if (!user) return res.status(401).json({ error: "invalid token" });

  await user.setPassword(req.body.newPassword);
  await user.save();
  res.json({ ok: true });
}

async function findAccount(req, res) {
  const account = await Account.findOne({ ownerId: req.query.ownerId });
  res.json(account);
}
