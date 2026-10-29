// Firebase 로그인·저장 연결.
// app.html은 Claude 아티팩트용 저장 인터페이스(claude.use("db"|"user"|"downloads"))로 짜여 있어서,
// 여기서 같은 모양의 객체를 Firebase로 구현해 window.claude에 붙인다.
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import {
  getAuth, GoogleAuthProvider, onAuthStateChanged, signInWithPopup, signInWithRedirect,
  getRedirectResult, signOut, setPersistence, browserLocalPersistence,
  createUserWithEmailAndPassword, signInWithEmailAndPassword, sendPasswordResetEmail,
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import {
  getFirestore, doc, getDoc, setDoc, collection, getDocs,
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-firestore.js";

const firebaseConfig = {
  apiKey: "AIzaSyBSpHxsAAc8_Q1Qj0OE433hRfxJuEkQNyM",
  authDomain: "minbeop-2f119.firebaseapp.com",
  projectId: "minbeop-2f119",
  storageBucket: "minbeop-2f119.firebasestorage.app",
  messagingSenderId: "175607410608",
  appId: "1:175607410608:web:49a3cd645e5378a836f075",
};

const fbApp = initializeApp(firebaseConfig);
const auth = getAuth(fbApp);
const fs = getFirestore(fbApp);
let currentUser = null;

// app.html의 경로 "data/users/<uid>" (컬렉션) → Firestore "users/<uid>/docs"
function mapCollection(path) {
  const m = /^data\/users\/([^/]+)$/.exec(path);
  if (!m) throw new TypeError("unsupported collection path: " + path);
  return ["users", m[1], "docs"];
}
// Firestore는 배열 안의 배열을 저장할 수 없어서 문서 본문을 JSON 문자열로 감싼다.
const pack = (data) => ({ json: JSON.stringify(data), updated: Date.now() });
const unpack = (raw) => { try { return raw && typeof raw.json === "string" ? JSON.parse(raw.json) : raw; } catch { return undefined; } };

function docRef(colPath, id) {
  const ref = doc(fs, ...colPath, id);
  return {
    id,
    get: async () => {
      const s = await getDoc(ref);
      const data = s.exists() ? unpack(s.data()) : undefined;
      return { id, exists: s.exists() && data !== undefined, data: () => data };
    },
    set: (data) => setDoc(ref, pack(data)),
  };
}
const dbShim = {
  collection(path) {
    const colPath = mapCollection(path);
    return {
      doc: (id) => docRef(colPath, id),
      get: async () => {
        const q = await getDocs(collection(fs, ...colPath));
        return { docs: q.docs.map((d) => { const data = unpack(d.data()); return { id: d.id, exists: true, data: () => data }; }) };
      },
    };
  },
};
const userShim = { id: async () => (currentUser ? currentUser.uid : null) };
const downloadsShim = {
  save: async ({ filename, data }) => {
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
  },
};
window.claude = {
  use: async (name) => (name === "db" ? dbShim : name === "user" ? userShim : name === "downloads" ? downloadsShim : null),
};

function messageFor(err) {
  const code = (err && err.code) || "";
  if (code === "auth/unauthorized-domain") return "Firebase 승인된 도메인에 이 사이트 주소가 없어요. Authentication 설정에서 도메인을 추가해 주세요.";
  if (code === "auth/operation-not-allowed") return "Firebase에서 이 로그인 방법이 아직 꺼져 있어요. Authentication → 로그인 방법에서 이메일/비밀번호(또는 Google)를 켜 주세요.";
  if (code === "auth/network-request-failed") return "인터넷 연결을 확인하고 다시 시도해 주세요.";
  if (code === "auth/invalid-credential" || code === "auth/wrong-password" || code === "auth/user-not-found" || code === "auth/invalid-login-credentials")
    return "이메일 또는 비밀번호가 맞지 않아요. 처음이면 '회원가입'에서 계정을 만들어 주세요.";
  if (code === "auth/email-already-in-use") return "이미 가입된 이메일이에요. '로그인'에서 로그인하거나, Google로 가입했다면 Google로 로그인해 주세요.";
  if (code === "auth/weak-password") return "비밀번호는 6자 이상이어야 해요.";
  if (code === "auth/invalid-email") return "이메일 주소를 확인해 주세요.";
  if (code === "auth/too-many-requests") return "시도가 너무 많아 잠시 막혔어요. 몇 분 뒤 다시 시도하거나 비밀번호를 재설정해 주세요.";
  if (code === "auth/account-exists-with-different-credential") return "이 이메일은 다른 방법(이메일 또는 Google)으로 가입되어 있어요. 그 방법으로 로그인해 주세요.";
  if (code === "auth/popup-closed-by-user" || code === "auth/cancelled-popup-request") return "";
  return "로그인하지 못했어요 (" + (code || "알 수 없는 오류") + ").";
}

function start() {
  const app = window.__dumunja;
  const A = app.auth;
  A.available = true;
  A.signIn = async () => {
    A.busy = true; A.error = ""; app.renderAuth();
    const provider = new GoogleAuthProvider();
    provider.setCustomParameters({ prompt: "select_account" });
    try {
      await setPersistence(auth, browserLocalPersistence);
      await signInWithPopup(auth, provider);
    } catch (e) {
      if (e && (e.code === "auth/popup-blocked" || e.code === "auth/operation-not-supported-in-this-environment")) {
        try { await signInWithRedirect(auth, provider); return; } catch (e2) { A.error = messageFor(e2); }
      } else A.error = messageFor(e);
    } finally { A.busy = false; app.renderAuth(); }
  };
  A.signOut = async () => { await signOut(auth); };
  const run = async (fn, okMsg) => {
    A.busy = true; A.error = ""; A.ok = false; app.renderAuth();
    try {
      await setPersistence(auth, browserLocalPersistence);
      await fn();
      if (okMsg) { A.error = okMsg; A.ok = true; }
    } catch (e) { A.error = messageFor(e); A.ok = false; }
    finally { A.busy = false; app.renderAuth(); }
  };
  A.emailSignIn = (email, pw) => run(() => signInWithEmailAndPassword(auth, email, pw));
  A.emailSignUp = (email, pw) => run(() => createUserWithEmailAndPassword(auth, email, pw));
  A.resetPassword = (email) => run(() => sendPasswordResetEmail(auth, email),
    "재설정 메일을 보냈어요. 메일의 링크에서 새 비밀번호를 정한 뒤 로그인해 주세요. 메일이 안 보이면 스팸함도 확인해 주세요.");
  getRedirectResult(auth).catch((e) => { A.error = messageFor(e); app.renderAuth(); });
  onAuthStateChanged(auth, (u) => {
    currentUser = u;
    A.user = u ? { email: u.email, name: u.displayName } : null;
    app.renderAuth();
    app.connect();
  });
}
if (window.__dumunja) start(); else window.__dumunjaReady = start;
