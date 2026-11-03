import React from 'react'
import { createRoot } from 'react-dom/client'
import './style.css'

function App() {
  const [tab, setTab] = React.useState('home')
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [token, setToken] = React.useState(localStorage.getItem('token') || '')
  const [notice, setNotice] = React.useState('Добро пожаловать в мастерскую Тайного Санты 🎄')
  const [gameTitle, setGameTitle] = React.useState('Наша новогодняя игра')
  const [invite, setInvite] = React.useState('')
  const [gameId, setGameId] = React.useState('')
  const [name, setName] = React.useState('')
  const [wishes, setWishes] = React.useState('')
  const api = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  async function request(path:string, method='GET', body?:unknown) {
    const r = await fetch(api + path, {method, headers:{'Content-Type':'application/json', ...(token ? {Authorization:`Bearer ${token}`} : {})}, ...(body ? {body:JSON.stringify(body)} : {})})
    const data = await r.json()
    if (!r.ok) throw new Error(data.detail || 'Ошибка запроса')
    return data
  }
  async function auth(kind:'register'|'login') {
    try { const d = await request(`/api/v1/auth/${kind}`, 'POST', {email,password}); setToken(d.access_token); localStorage.setItem('token',d.access_token); setNotice('Вы вошли в систему. Теперь можно создать игру или присоединиться.') }
    catch(e) { setNotice((e as Error).message) }
  }
  async function createGame() {
    try { const d = await request('/api/v1/games','POST',{title:gameTitle}); setGameId(d.id); setInvite(d.invite_code); setNotice('Игра создана! Передайте код приглашения участникам.') }
    catch(e) { setNotice((e as Error).message) }
  }
  async function joinGame() {
    try { const d = await request('/api/v1/games/join','POST',{invite_code:invite}); setGameId(d.game_id); setNotice('Вы присоединились к игре. Заполните анкету.') }
    catch(e) { setNotice((e as Error).message) }
  }
  async function saveProfile() {
    try { await request(`/api/v1/games/${gameId}/profile`,'PUT',{display_name:name,wishes}); setNotice('Анкета сохранена!') }
    catch(e) { setNotice((e as Error).message) }
  }
  async function draw() {
    try { const d = await request(`/api/v1/games/${gameId}/draw`,'POST',{}); setNotice(`Жеребьёвка завершена. Участников: ${d.participants_count}`) }
    catch(e) { setNotice((e as Error).message) }
  }
  async function showRecipient() {
    try { const d = await request(`/api/v1/games/${gameId}/my-recipient`); setNotice(`Твой подопечный: ${d.display_name}. Пожелания: ${d.wishes}`) }
    catch(e) { setNotice((e as Error).message) }
  }
  return <main>
    <header><div className="logo">🎁 <span>Тайный Санта</span></div><div className="snow">❄　✦　❄</div></header>
    <section className="hero"><div className="eyebrow">НОВОГОДНЯЯ МАСТЕРСКАЯ</div><h1>Подарки становятся<br/><em>маленьким чудом</em></h1><p>Создай игру, пригласи друзей и узнай, кому готовить сюрприз.</p></section>
    <nav>{[['home','Главная'],['account','Аккаунт'],['game','Моя игра']].map(([id,label])=><button className={tab===id?'active':''} onClick={()=>setTab(id)}>{label}</button>)}</nav>
    <section className="panel">
      <div className="notice">{notice}</div>
      {tab==='home' && <div className="two"><article><h2>✨ Создать игру</h2><p>Стань организатором и пригласи участников.</p><input value={gameTitle} onChange={e=>setGameTitle(e.target.value)} placeholder="Название игры"/><button className="primary" onClick={createGame} disabled={!token}>Создать игру</button></article><article><h2>🧣 Присоединиться</h2><p>Введи код приглашения от организатора.</p><input value={invite} onChange={e=>setInvite(e.target.value)} placeholder="Код приглашения"/><button className="primary" onClick={joinGame} disabled={!token}>Вступить в игру</button></article></div>}
      {tab==='account' && <article><h2>🔐 Вход или регистрация</h2><input value={email} onChange={e=>setEmail(e.target.value)} placeholder="Email" type="email"/><input value={password} onChange={e=>setPassword(e.target.value)} placeholder="Пароль (от 10 символов)" type="password"/><div className="actions"><button className="primary" onClick={()=>auth('register')}>Зарегистрироваться</button><button onClick={()=>auth('login')}>Войти</button></div></article>}
      {tab==='game' && <article><h2>📝 Анкета участника</h2><input value={gameId} onChange={e=>setGameId(e.target.value)} placeholder="ID игры (после создания или вступления)"/><input value={name} onChange={e=>setName(e.target.value)} placeholder="Как тебя зовут?"/><textarea value={wishes} onChange={e=>setWishes(e.target.value)} placeholder="Что ты хочешь получить в подарок?"/><div className="actions"><button className="primary" onClick={saveProfile}>Сохранить анкету</button><button onClick={showRecipient}>Мой подопечный</button><button onClick={draw}>Провести жеребьёвку (администратор)</button></div></article>}
    </section>
    <footer>Сделано с теплом и щепоткой новогоднего волшебства · MVP 0.1</footer>
  </main>
}
createRoot(document.getElementById('root')!).render(<App/>)
