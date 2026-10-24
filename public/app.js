'use strict';

const socket = io({
  transports: ['websocket', 'polling'],
  reconnectionAttempts: 20,
  reconnectionDelay: 1000,
  reconnection: true
});

let currentUser = null;
let isSignup = false;
let currentStream = null;
let peer = null;
let incomingData = null;
let activeChatUser = null;
let activeCallUser = null;
let activeCallIsVideo = false;
let groupPeers = {};
let joinedGroupCall = false;
let selectedRingtone = 'classic';

let iceServersConfig = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' }
  ]
};

// Load optional TURN settings from the server; TURN improves reliability on some cellular networks.
fetch('/api/webrtc-config', { cache: 'no-store' })
  .then(response => response.ok ? response.json() : null)
  .then(config => {
    if (config && Array.isArray(config.iceServers) && config.iceServers.length) {
      iceServersConfig = { iceServers: config.iceServers };
    }
  })
  .catch(error => console.warn('ICE configuration unavailable; using STUN only:', error));

const $ = id => document.getElementById(id);
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, ch => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[ch]));

function getActiveRingtone(style = $('ring-style-select')?.value || selectedRingtone) {
  selectedRingtone = style;
  if (style === 'modern') return $('ring-modern');
  if (style === 'soft') return $('ring-soft');
  return $('ring-classic');
}

function stopRingtone() {
  ['ring-classic', 'ring-modern', 'ring-soft'].forEach(id => {
    const audio = $(id);
    if (audio) { audio.pause(); audio.currentTime = 0; }
  });
}

function showNotice(message, isError = false) {
  const banner = $('notification-banner');
  if (!banner) { alert(message); return; }
  banner.textContent = message;
  banner.style.display = 'block';
  banner.style.background = isError ? '#ffebee' : '#e8f5e9';
  banner.style.borderColor = isError ? '#ef9a9a' : '#a5d6a7';
  banner.style.color = isError ? '#c62828' : '#256029';
}

function toggleAuthMode() {
  isSignup = !isSignup;
  $('auth-title').textContent = isSignup ? 'Signup' : 'Login';
  $('auth-btn').textContent = isSignup ? 'Signup' : 'Login';
  $('auth-phone').style.display = isSignup ? '' : 'none';
  $('auth-bio').style.display = isSignup ? '' : 'none';
}

async function handleAuth() {
  const username = $('auth-username').value.trim();
  const password = $('auth-password').value;
  const phone = $('auth-phone').value.trim();
  const bio = $('auth-bio').value.trim();
  if (!username || !password) return alert('Username fi password guuti.');

  const button = $('auth-btn');
  button.disabled = true;
  try {
    const response = await fetch(isSignup ? '/api/auth/signup' : '/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, phone, bio })
    });
    const data = await response.json();
    if (!response.ok || !data.success) return alert(data.message || 'Login/signup hin milkoofne.');

    currentUser = data.user;
    $('auth-sec').style.display = 'none';
    $('app-sec').style.display = 'block';
    const adminLink = currentUser.is_admin
      ? '<a href="admin.html" style="color:#1877f2;margin-left:10px">Admin Dashboard</a>' : '';
    $('user-head-sec').innerHTML = `<b>@${escapeHTML(currentUser.username)}</b> ${adminLink}
      <button id="logout-btn" class="btn btn-danger" style="width:auto;padding:5px;margin-left:5px">Logout</button>`;
    $('logout-btn').addEventListener('click', logout);
    socket.emit('register-user', currentUser.username);
    await loadPosts();
  } catch (error) {
    console.error('Auth error:', error);
    alert('Server waliin wal qunnamuun hin danda’amne. Internet fi server ilaali.');
  } finally {
    button.disabled = false;
  }
}

function logout() {
  endCall(false);
  socket.disconnect();
  location.reload();
}

socket.on('connect', () => {
  if (currentUser) socket.emit('register-user', currentUser.username);
});
socket.on('connect_error', err => console.warn('Socket connection error:', err.message));

socket.on('missed-calls-notification', missedList => {
  if (!Array.isArray(missedList) || !missedList.length) return;
  const banner = $('notification-banner');
  if (!banner) return;
  banner.style.display = 'block';
  const heading = document.createElement('b');
  heading.textContent = '🔔 Missed calls';
  const list = document.createElement('ul');
  missedList.forEach(item => {
    const li = document.createElement('li');
    li.textContent = `@${item.caller} irraa ${item.call_type} call dhufeera (${item.created_at || ''})`;
    list.appendChild(li);
  });
  banner.replaceChildren(heading, list);
});

socket.on('update-user-list', users => {
  const container = $('users-list');
  if (!container || !currentUser || !Array.isArray(users)) return;
  container.replaceChildren();
  users.filter(user => user.username !== currentUser.username).forEach(user => {
    const row = document.createElement('div');
    row.className = 'user-list-item';
    const left = document.createElement('div');
    const dot = document.createElement('span');
    dot.className = `status-dot ${user.isOnline ? 'online' : 'offline'}`;
    left.append(dot, document.createTextNode(` @${user.username} `));
    const right = document.createElement('div');
    right.innerHTML = `<button class="btn btn-primary" style="width:auto;padding:5px" data-action="chat">Chat 💬</button>
      ${user.isOnline ? '<button class="btn btn-green" style="width:auto;padding:5px" data-action="voice">Voice 📞</button><button class="btn btn-primary" style="width:auto;padding:5px" data-action="video">Video 📹</button>' : '<small>Offline</small>'}`;
    right.querySelector('[data-action="chat"]').addEventListener('click', () => openPrivateChat(user.username));
    right.querySelector('[data-action="voice"]')?.addEventListener('click', () => startCall(user.username, false));
    right.querySelector('[data-action="video"]')?.addEventListener('click', () => startCall(user.username, true));
    row.append(left, right);
    container.appendChild(row);
  });
});

function mediaMarkup(data) {
  const url = data.media_url || data.mediaUrl;
  const type = data.media_type || data.mediaType;
  if (!url) return '';
  if (type === 'video') return `<br><video src="${escapeHTML(url)}" controls playsinline style="max-width:180px;width:100%"></video>`;
  if (type === 'audio') return `<br><audio src="${escapeHTML(url)}" controls></audio>`;
  return `<br><img src="${escapeHTML(url)}" alt="media" style="max-width:180px;width:100%;border-radius:5px">`;
}

function sendGroupMessage() {
  if (!currentUser) return;
  const input = $('group-msg-input');
  const fileInput = $('group-media-input');
  const message = input.value.trim();
  const file = fileInput.files[0];
  if (!file && !message) return;
  if (file && file.size > 15 * 1024 * 1024) return alert('Faayilli 15 MB caaluu hin qabu.');
  const send = (mediaUrl = null, mediaType = null) => {
    socket.emit('group-chat-message', { sender: currentUser.username, message, mediaUrl, mediaType });
    input.value = '';
    fileInput.value = '';
  };
  if (!file) return send();
  const reader = new FileReader();
  reader.onload = event => send(event.target.result, file.type.startsWith('video/') ? 'video' : file.type.startsWith('audio/') ? 'audio' : 'image');
  reader.onerror = () => alert('Faayila dubbisuun hin danda’amne.');
  reader.readAsDataURL(file);
}

socket.on('group-chat-message', data => {
  const box = $('group-chat-box');
  if (!box) return;
  const item = document.createElement('div');
  item.innerHTML = `<b>@${escapeHTML(data.sender)}:</b> ${escapeHTML(data.message || '')}${mediaMarkup(data)}`;
  box.appendChild(item);
  box.scrollTop = box.scrollHeight;
});

function openPrivateChat(username) {
  activeChatUser = username;
  $('private-chat-title').textContent = `Chat @${username} wajjin`;
  $('private-chat-section').style.display = 'block';
  $('private-chat-box').replaceChildren();
}
function closePrivateChat() {
  activeChatUser = null;
  $('private-chat-section').style.display = 'none';
}

function sendPrivateMessage() {
  if (!currentUser || !activeChatUser) return;
  const input = $('private-msg-input');
  const fileInput = $('private-media-input');
  const message = input.value.trim();
  const file = fileInput.files[0];
  if (!file && !message) return;
  if (file && file.size > 15 * 1024 * 1024) return alert('Faayilli 15 MB caaluu hin qabu.');
  const send = (mediaUrl = null, mediaType = null) => {
    const payload = { sender: currentUser.username, receiver: activeChatUser, message, mediaUrl, mediaType };
    socket.emit('private-message', payload);
    appendPrivateMessage(payload, true);
    input.value = '';
    fileInput.value = '';
  };
  if (!file) return send();
  const reader = new FileReader();
  reader.onload = event => send(event.target.result, file.type.startsWith('video/') ? 'video' : file.type.startsWith('audio/') ? 'audio' : 'image');
  reader.onerror = () => alert('Faayila dubbisuun hin danda’amne.');
  reader.readAsDataURL(file);
}

function appendPrivateMessage(data, outgoing = false) {
  const box = $('private-chat-box');
  if (!box) return;
  const item = document.createElement('div');
  item.style.textAlign = outgoing ? 'right' : 'left';
  item.innerHTML = `<b>${outgoing ? 'Ani' : '@' + escapeHTML(data.sender)}:</b> ${escapeHTML(data.message || '')}${mediaMarkup(data)}`;
  box.appendChild(item);
  box.scrollTop = box.scrollHeight;
}

socket.on('private-message', data => {
  if (activeChatUser === data.sender) appendPrivateMessage(data, false);
  else alert(`Ergaa haaraan @${data.sender} irraa dhufeera!`);
});

function resetVideoGrid(showLocal = false) {
  const grid = $('video-grid');
  if (!grid) return;
  grid.replaceChildren();
  if (showLocal) {
    const local = document.createElement('video');
    local.id = 'local-video'; local.autoplay = true; local.muted = true; local.playsInline = true;
    grid.appendChild(local);
    if (currentStream) local.srcObject = currentStream;
  }
}

function attachPeerHandlers(p, remoteId = 'remote-video') {
  p.on('stream', remoteStream => {
    let remote = $(remoteId);
    if (!remote) {
      remote = document.createElement('video');
      remote.id = remoteId; remote.autoplay = true; remote.playsInline = true;
      $('video-grid')?.appendChild(remote);
    }
    remote.srcObject = remoteStream;
    remote.play().catch(error => console.warn('Remote playback needs user action:', error));
  });
  p.on('error', error => {
    console.error('WebRTC peer error:', error);
    showNotice('Call connection dogoggoreera. Network ykn TURN server ilaali.', true);
  });
  p.on('close', () => console.log('Peer connection closed'));
}

async function getCallMedia(isVideo) {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error('Camera/microphone hin deeggaramu. HTTPS irratti banuu qabda.');
  }
  return navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    video: isVideo ? { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' } : false
  });
}

async function startCall(userToCall, isVideo) {
  if (!currentUser) return alert('Dura login godhi.');
  if (peer || currentStream) return alert('Call biraa irratti hirmaachaa jirta. Dura call sana cufi.');
  activeCallUser = userToCall;
  activeCallIsVideo = isVideo;
  try {
    currentStream = await getCallMedia(isVideo);
    $('call-screen').style.display = 'block';
    resetVideoGrid(true);
    peer = new SimplePeer({ initiator: true, trickle: false, stream: currentStream, config: iceServersConfig });
    attachPeerHandlers(peer);
    peer.on('signal', signalData => socket.emit('call-user', {
      userToCall, signalData, callerName: currentUser.username, isVideo,
      ringStyle: $('ring-style-select')?.value || 'classic'
    }));
    peer.on('close', () => { if (peer) peer = null; });
  } catch (error) {
    console.error('Start call error:', error);
    endCall(false);
    alert(error.message || 'Camera ykn microphone eeyyama gaafata. Browser settings keessatti hayyami.');
  }
}

socket.on('incoming-call', data => {
  if (peer || currentStream) {
    socket.emit('reject-call', { to: data.from });
    return;
  }
  incomingData = data;
  const style = data.ringStyle || $('ring-style-select')?.value || 'classic';
  $('caller-name-txt').textContent = `${data.callerName} si bilbilaa jira...`;
  $('call-modal').style.display = 'flex';
  const ring = getActiveRingtone(style);
  if (ring) { ring.currentTime = 0; ring.play().catch(error => console.warn('Ringtone blocked:', error)); }
});

async function acceptCall() {
  if (!incomingData) return;
  stopRingtone();
  const callData = incomingData;
  $('call-modal').style.display = 'none';
  activeCallUser = callData.callerName;
  activeCallIsVideo = !!callData.isVideo;
  try {
    currentStream = await getCallMedia(activeCallIsVideo);
    $('call-screen').style.display = 'block';
    resetVideoGrid(true);
    peer = new SimplePeer({ initiator: false, trickle: false, stream: currentStream, config: iceServersConfig });
    attachPeerHandlers(peer);
    peer.on('signal', signal => socket.emit('accept-call', { signal, to: callData.from }));
    peer.signal(callData.signal);
    incomingData = null;
  } catch (error) {
    console.error('Accept call error:', error);
    socket.emit('reject-call', { to: callData.from });
    endCall(false);
    alert(error.message || 'Camera/microphone eeyyama kennuu qabda.');
  }
}

function rejectCall() {
  stopRingtone();
  $('call-modal').style.display = 'none';
  if (incomingData?.from) socket.emit('reject-call', { to: incomingData.from });
  incomingData = null;
}

socket.on('call-accepted', signal => {
  if (peer && signal) {
    try { peer.signal(signal); } catch (error) { console.error('Accept signal error:', error); }
  }
});
socket.on('call-rejected', () => {
  alert('Namni bilbilli itti godhame call dide.');
  endCall(false);
});
socket.on('end-call', () => endCall(false));
socket.on('call-error', data => {
  showNotice(data?.message || 'Call dogoggoreera.', true);
  endCall(false);
});
socket.on('call-failed-offline', () => {
  alert('Maammilli offline dha. Missed call galmaa’eera.');
  endCall(false);
});

async function startGroupCall() {
  if (!currentUser) return alert('Dura login godhi.');
  if (currentStream) return alert('Call duraan jalqabameera.');
  try {
    currentStream = await getCallMedia(true);
    $('call-screen').style.display = 'block';
    resetVideoGrid(true);
    joinedGroupCall = true;
    socket.emit('join-group-call');
  } catch (error) {
    console.error('Group call error:', error);
    endCall(false);
    alert(error.message || 'Camera/microphone eeyyama kennuu qabda.');
  }
}

socket.on('user-joined-group', userId => {
  if (!currentStream || !joinedGroupCall || groupPeers[userId]) return;
  const p = new SimplePeer({ initiator: true, trickle: false, stream: currentStream, config: iceServersConfig });
  groupPeers[userId] = p;
  attachPeerHandlers(p, `remote-${userId}`);
  p.on('signal', signal => socket.emit('group-signal', { signal, to: userId }));
});

socket.on('group-signal', data => {
  if (!currentStream || !joinedGroupCall || !data?.from) return;
  let p = groupPeers[data.from];
  if (!p) {
    p = new SimplePeer({ initiator: false, trickle: false, stream: currentStream, config: iceServersConfig });
    groupPeers[data.from] = p;
    attachPeerHandlers(p, `remote-${data.from}`);
    p.on('signal', signal => socket.emit('group-signal', { signal, to: data.from }));
  }
  try { p.signal(data.signal); } catch (error) { console.error('Group signal error:', error); }
});

socket.on('user-left-group', userId => {
  if (groupPeers[userId]) { groupPeers[userId].destroy(); delete groupPeers[userId]; }
  $(`remote-${userId}`)?.remove();
});

function endCall(notifyRemote = true) {
  stopRingtone();
  if (notifyRemote && activeCallUser) socket.emit('end-call', { to: activeCallUser });
  if (peer) { try { peer.destroy(); } catch (_) {} peer = null; }
  Object.values(groupPeers).forEach(p => { try { p.destroy(); } catch (_) {} });
  groupPeers = {};
  if (joinedGroupCall) socket.emit('leave-group-call');
  joinedGroupCall = false;
  if (currentStream) {
    currentStream.getTracks().forEach(track => track.stop());
    currentStream = null;
  }
  activeCallUser = null;
  activeCallIsVideo = false;
  incomingData = null;
  if ($('call-screen')) $('call-screen').style.display = 'none';
  if ($('call-modal')) $('call-modal').style.display = 'none';
  resetVideoGrid(false);
}

function submitPost() {
  if (!currentUser) return alert('Dura login godhi.');
  const content = $('post-text').value.trim();
  const fileInput = $('post-file');
  const file = fileInput.files[0];
  if (!content && !file) return alert('Barreeffama ykn faayila filadhu.');
  if (file && file.size > 15 * 1024 * 1024) return alert('Faayilli 15 MB caaluu hin qabu.');
  const send = (mediaUrl = null, mediaType = null) => {
    socket.emit('create-post', { username: currentUser.username, content, mediaUrl, mediaType });
    alert('Post-n keessan ergameera.');
    $('post-text').value = '';
    fileInput.value = '';
  };
  if (!file) return send();
  const reader = new FileReader();
  reader.onload = event => send(event.target.result, file.type.startsWith('video/') ? 'video' : 'image');
  reader.onerror = () => alert('Faayila dubbisuun hin danda’amne.');
  reader.readAsDataURL(file);
}

async function loadPosts() {
  try {
    const response = await fetch('/api/posts');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const posts = await response.json();
    const feed = $('feed-container');
    if (!feed) return;
    feed.replaceChildren();
    posts.forEach(post => {
      const card = document.createElement('div');
      card.className = 'post';
      const content = document.createElement('p');
      content.textContent = post.content || '';
      card.innerHTML = `<b>@${escapeHTML(post.username)}</b>`;
      card.appendChild(content);
      if (post.media_url && post.media_type === 'image') {
        const image = document.createElement('img'); image.src = post.media_url; image.alt = 'Post image'; card.appendChild(image);
      } else if (post.media_url && post.media_type === 'video') {
        const video = document.createElement('video'); video.src = post.media_url; video.controls = true; video.playsInline = true; card.appendChild(video);
      }
      feed.appendChild(card);
    });
  } catch (error) {
    console.error('Load posts error:', error);
    showNotice('Post fe’uun hin danda’amne. Server/database ilaali.', true);
  }
}

// Start in login mode; hide signup-only fields until Signup is selected.
if ($('auth-phone')) $('auth-phone').style.display = 'none';
if ($('auth-bio')) $('auth-bio').style.display = 'none';
