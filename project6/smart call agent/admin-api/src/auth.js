const jwt = require('jsonwebtoken');
const { staffUsers } = require('./mockStore');

const JWT_SECRET = process.env.JWT_SECRET || 'smart-call-agent-dev-secret';

function createToken(user) {
  return jwt.sign({ sub: user.id, email: user.email, role: user.role }, JWT_SECRET, {
    expiresIn: '6h',
  });
}

function verifyToken(token) {
  if (!token) {
    throw Object.assign(new Error('Missing token'), { statusCode: 401 });
  }

  try {
    return jwt.verify(token, JWT_SECRET);
  } catch (err) {
    throw Object.assign(new Error('Invalid token'), { statusCode: 401 });
  }
}

function login({ email, password }) {
  const user = staffUsers.find((candidate) => candidate.email === email && candidate.password === password);

  if (!user) {
    throw Object.assign(new Error('Invalid email or password'), { statusCode: 401 });
  }

  return {
    token: createToken(user),
    user: {
      id: user.id,
      name: user.name,
      email: user.email,
      role: user.role,
      locationId: user.locationId,
    },
  };
}

function requireRole(role) {
  return (req, res, next) => {
    if (!req.user || req.user.role !== role) {
      return res.status(403).json({ error: 'forbidden', message: `Role ${role} required` });
    }
    return next();
  };
}

module.exports = {
  login,
  verifyToken,
  requireRole,
};
