import { useEffect, useState } from 'react'
import { api, tg } from './api'

const WEEKDAYS_RU = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
const MONTHS_RU = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']

function fmtMoney(n) {
  return Math.round(n).toLocaleString('ru-RU').replace(/,/g, ' ')
}

function fmtDate(iso) {
  const d = new Date(iso)
  return `${WEEKDAYS_RU[(d.getDay() + 6) % 7]} ${d.getDate()} ${MONTHS_RU[d.getMonth()]}`
}

export default function App() {
  useEffect(() => {
    tg?.ready()
    tg?.expand()
  }, [])

  const [screen, setScreen] = useState('home')

  return (
    <div className="screen">
      {screen === 'home' && <Home onNavigate={setScreen} />}
      {screen === 'booking' && <Booking onBack={() => setScreen('home')} />}
      {screen === 'referral' && <Referral onBack={() => setScreen('home')} />}
      {screen === 'level' && <Level onBack={() => setScreen('home')} />}
      {screen === 'gifts' && <Gifts onBack={() => setScreen('home')} />}
      {screen === 'admin' && <AdminPanel onBack={() => setScreen('home')} />}
    </div>
  )
}

// ---------- Home ----------

function Home({ onNavigate }) {
  const [me, setMe] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getMe().then(setMe).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="error">{error}</div>
  if (!me) return <div className="loading">Загрузка…</div>

  return (
    <div>
      <div className="balance-hero">
        <div className="label">Бонусный баланс</div>
        <div className="amount">{fmtMoney(me.bonus_balance)}</div>
        <div className="label">Уровень {me.level_name} · {me.bonus_percent}% с визита</div>
      </div>

      <button className="list-item" onClick={() => onNavigate('booking')}>
        <span>📅 Записаться на приём</span>
        <span>›</span>
      </button>
      <button className="list-item" onClick={() => onNavigate('level')}>
        <span>⭐ Мой уровень</span>
        <span>›</span>
      </button>
      <button className="list-item" onClick={() => onNavigate('gifts')}>
        <span>🎁 Бонусы и подарки</span>
        <span>›</span>
      </button>
      <button className="list-item" onClick={() => onNavigate('referral')}>
        <span>👥 Пригласить друга</span>
        <span>›</span>
      </button>

      {me.is_admin && (
        <button className="list-item" onClick={() => onNavigate('admin')} style={{ marginTop: 16, borderColor: 'var(--accent)' }}>
          <span>🛠 Админ-панель</span>
          <span>›</span>
        </button>
      )}
    </div>
  )
}

// ---------- Booking ----------

function Booking({ onBack }) {
  const [step, setStep] = useState('service') // service -> doctor -> date -> slot -> confirm -> done
  const [services, setServices] = useState(null)
  const [doctors, setDoctors] = useState(null)
  const [dates, setDates] = useState(null)
  const [slots, setSlots] = useState(null)

  const [service, setService] = useState(null)
  const [doctor, setDoctor] = useState(null)
  const [date, setDate] = useState(null)
  const [slot, setSlot] = useState(null)

  const [error, setError] = useState(null)
  const [booking, setBooking] = useState(false)

  useEffect(() => {
    api.getServices().then(setServices).catch((e) => setError(e.message))
  }, [])

  function chooseService(s) {
    setService(s)
    setDoctors(null)
    setStep('doctor')
    api.getDoctors(s.id).then(setDoctors).catch((e) => setError(e.message))
  }

  function chooseDoctor(d) {
    setDoctor(d)
    setDates(null)
    setStep('date')
    api.getDates(d.id).then(setDates).catch((e) => setError(e.message))
  }

  function chooseDate(d) {
    setDate(d)
    setSlots(null)
    setStep('slot')
    api.getSlots(doctor.id, d).then(setSlots).catch((e) => setError(e.message))
  }

  function chooseSlot(s) {
    setSlot(s)
    setStep('confirm')
  }

  async function confirmBooking() {
    setBooking(true)
    setError(null)
    try {
      await api.book(service.id, doctor.id, slot.id)
      setStep('done')
      tg?.HapticFeedback?.notificationOccurred('success')
    } catch (e) {
      if (e.message.includes('409') || e.message.toLowerCase().includes('занят')) {
        setError('Этот слот только что заняли. Пожалуйста, выберите другое время.')
        setStep('slot')
        api.getSlots(doctor.id, date).then(setSlots)
      } else {
        setError(e.message)
      }
    } finally {
      setBooking(false)
    }
  }

  return (
    <div>
      <div className="title">Запись на приём</div>

      {error && <div className="error">{error}</div>}

      {step === 'service' && (
        <List
          items={services}
          render={(s) => (
            <>
              <span>{s.name}</span>
              <span className="price">{fmtMoney(s.price)} сум</span>
            </>
          )}
          onSelect={chooseService}
        />
      )}

      {step === 'doctor' && (
        <List
          items={doctors}
          render={(d) => (
            <>
              <span>{d.full_name}</span>
              <span className="price">{d.shift || d.specialization}</span>
            </>
          )}
          onSelect={chooseDoctor}
          onBack={() => setStep('service')}
        />
      )}

      {step === 'date' && (
        <>
          <div className="grid">
            {(dates || []).map((d) => (
              <div key={d} className="chip" onClick={() => chooseDate(d)}>
                {fmtDate(d)}
              </div>
            ))}
          </div>
          {dates && dates.length === 0 && <div className="empty">Нет свободных дат</div>}
          {!dates && <div className="loading">Загрузка…</div>}
          <button className="btn-secondary" onClick={() => setStep('doctor')}>⬅️ Назад</button>
        </>
      )}

      {step === 'slot' && (
        <>
          <div className="grid cols-4">
            {(slots || []).map((s) => (
              <div key={s.id} className="chip" onClick={() => chooseSlot(s)}>
                {s.start_time}
              </div>
            ))}
          </div>
          {slots && slots.length === 0 && <div className="empty">Нет свободного времени</div>}
          {!slots && <div className="loading">Загрузка…</div>}
          <button className="btn-secondary" onClick={() => setStep('date')}>⬅️ Назад</button>
        </>
      )}

      {step === 'confirm' && (
        <div className="card">
          <div><b>Услуга:</b> {service.name}</div>
          <div><b>Врач:</b> {doctor.full_name}</div>
          <div><b>Дата:</b> {fmtDate(date)}, {slot.start_time}</div>
          <div><b>Стоимость:</b> {fmtMoney(service.price)} сум</div>
          <br />
          <button className="btn-primary" disabled={booking} onClick={confirmBooking}>
            {booking ? 'Отправка…' : 'Подтвердить запись'}
          </button>
          <button className="btn-secondary" onClick={() => setStep('slot')}>⬅️ Назад</button>
        </div>
      )}

      {step === 'done' && (
        <div className="card">
          ✅ Заявка отправлена! Администратор подтвердит запись, вам придёт уведомление в чат с ботом.
          <br /><br />
          <button className="btn-primary" onClick={onBack}>На главную</button>
        </div>
      )}

      {step === 'service' && (
        <button className="btn-secondary" onClick={onBack}>⬅️ На главную</button>
      )}
    </div>
  )
}

function List({ items, render, onSelect, onBack }) {
  if (!items) return <div className="loading">Загрузка…</div>
  if (items.length === 0) return <div className="empty">Ничего не найдено</div>
  return (
    <>
      {items.map((item) => (
        <button key={item.id} className="list-item" onClick={() => onSelect(item)}>
          {render(item)}
        </button>
      ))}
      {onBack && <button className="btn-secondary" onClick={onBack}>⬅️ Назад</button>}
    </>
  )
}

// ---------- Admin Panel ----------

const STATUS_LABELS = {
  pending: 'Ожидает подтверждения',
  confirmed: 'Подтверждена',
  completed: 'Завершена',
  cancelled_by_patient: 'Отменена пациентом',
  cancelled_by_admin: 'Отклонена админом',
  awaiting_reschedule: 'Ждём ответ на перенос',
}

function AdminPanel({ onBack }) {
  const [view, setView] = useState('home') // home -> list -> detail, or calendar
  const [status, setStatus] = useState('pending')
  const [selectedId, setSelectedId] = useState(null)

  return (
    <div>
      {view === 'home' && (
        <AdminHome
          onBack={onBack}
          onOpenList={(s) => { setStatus(s); setView('list') }}
          onOpenCalendar={() => setView('calendar')}
        />
      )}
      {view === 'list' && (
        <AdminList
          status={status}
          onChangeStatus={setStatus}
          onOpen={(id) => { setSelectedId(id); setView('detail') }}
          onBack={() => setView('home')}
        />
      )}
      {view === 'detail' && (
        <AdminDetail
          id={selectedId}
          onBack={() => setView('list')}
          onDone={() => setView('list')}
        />
      )}
      {view === 'calendar' && (
        <AdminCalendar onBack={() => setView('home')} onOpen={(id) => { setSelectedId(id); setView('detail') }} />
      )}
    </div>
  )
}

function AdminHome({ onBack, onOpenList, onOpenCalendar }) {
  const [stats, setStats] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.adminStats().then(setStats).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="error">{error}</div>
  if (!stats) return <div className="loading">Загрузка…</div>

  return (
    <div>
      <div className="title">🛠 Админ-панель</div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
        <div className="card" onClick={() => onOpenList('pending')} style={{ cursor: 'pointer' }}>
          <div className="subtitle">Ожидают подтверждения</div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{stats.pending_count}</div>
        </div>
        <div className="card" onClick={() => onOpenList('confirmed')} style={{ cursor: 'pointer' }}>
          <div className="subtitle">Подтверждено</div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{stats.confirmed_count}</div>
        </div>
        <div className="card">
          <div className="subtitle">Завершено сегодня</div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{stats.completed_today}</div>
        </div>
        <div className="card">
          <div className="subtitle">Завершено за месяц</div>
          <div style={{ fontSize: 24, fontWeight: 700 }}>{stats.completed_this_month}</div>
        </div>
      </div>

      <div className="balance-hero">
        <div className="label">Выручка за месяц</div>
        <div className="amount">{fmtMoney(stats.revenue_this_month)} сум</div>
      </div>

      <div className="card">
        <div>👥 Всего пациентов: {stats.total_patients}</div>
        <div>🆕 Новых сегодня: {stats.new_patients_today}</div>
        {stats.awaiting_reschedule_count > 0 && (
          <div>🔄 Ждут ответа на перенос: {stats.awaiting_reschedule_count}</div>
        )}
      </div>

      <button className="list-item" onClick={() => onOpenList('pending')}>
        <span>📋 Заявки на подтверждение</span><span>›</span>
      </button>
      <button className="list-item" onClick={() => onOpenList('confirmed')}>
        <span>✅ Подтверждённые записи</span><span>›</span>
      </button>
      <button className="list-item" onClick={() => onOpenList('completed')}>
        <span>🗂 История завершённых</span><span>›</span>
      </button>
      <button className="list-item" onClick={onOpenCalendar}>
        <span>📅 Календарь по дням</span><span>›</span>
      </button>

      <button className="btn-secondary" onClick={onBack}>⬅️ На главную</button>
    </div>
  )
}

function AdminList({ status, onChangeStatus, onOpen, onBack }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setItems(null)
    api.adminAppointments(status).then(setItems).catch((e) => setError(e.message))
  }, [status])

  const tabs = [
    ['pending', 'Ожидают'],
    ['confirmed', 'Подтв.'],
    ['completed', 'Завершены'],
    ['cancelled_by_admin', 'Отклонены'],
  ]

  return (
    <div>
      <div className="title">Заявки</div>

      <div className="grid cols-4" style={{ marginBottom: 12 }}>
        {tabs.map(([key, label]) => (
          <div
            key={key}
            className="chip"
            onClick={() => onChangeStatus(key)}
            style={status === key ? { background: 'var(--accent)', color: 'white' } : {}}
          >
            {label}
          </div>
        ))}
      </div>

      {error && <div className="error">{error}</div>}
      {!items && !error && <div className="loading">Загрузка…</div>}
      {items && items.length === 0 && <div className="empty">Пусто</div>}

      {items && items.map((a) => (
        <button key={a.id} className="list-item" onClick={() => onOpen(a.id)}>
          <span>
            {a.patient_name}<br />
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{a.service_name} · {a.doctor_name}</span>
          </span>
          <span className="price">{a.formatted}</span>
        </button>
      ))}

      <button className="btn-secondary" onClick={onBack}>⬅️ Назад</button>
    </div>
  )
}

function AdminDetail({ id, onBack, onDone }) {
  const [a, setA] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [showAmountInput, setShowAmountInput] = useState(false)
  const [amount, setAmount] = useState('')

  function load() {
    api.adminAppointmentDetail(id).then(setA).catch((e) => setError(e.message))
  }

  useEffect(() => { load() }, [id])

  if (error) return <div className="error">{error}</div>
  if (!a) return <div className="loading">Загрузка…</div>

  async function handleConfirm() {
    setBusy(true)
    try { await api.adminConfirm(id); onDone() } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  async function handleDecline() {
    setBusy(true)
    try { await api.adminDecline(id); onDone() } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  async function handleComplete() {
    if (!amount || isNaN(Number(amount))) return
    setBusy(true)
    try { await api.adminComplete(id, Number(amount)); onDone() } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  return (
    <div>
      <div className="title">Заявка №{a.id}</div>
      <div className="subtitle">{STATUS_LABELS[a.status] || a.status}</div>

      <div className="card">
        <div className="subtitle">Клиент</div>
        <div><b>{a.patient_name}</b></div>
        {a.phone && <div>📱 {a.phone}</div>}
        <div>⭐ {a.level_name} ({a.bonus_percent}% с визита)</div>
        <div>💰 Баланс: {fmtMoney(a.bonus_balance)}</div>
        <div>Завершённых визитов: {a.completed_visits_count}{a.completed_visits_count === 0 ? ' (первый визит)' : ''}</div>
        {a.referral_status === 'pending' && <div>🔗 Пришёл по реферальной ссылке</div>}
      </div>

      <div className="card">
        <div className="subtitle">Врач</div>
        <div>{a.doctor_name} — {a.doctor_specialization}</div>
        <div>{a.doctor_shift}</div>
      </div>

      <div className="card">
        <div className="subtitle">Услуга</div>
        <div>{a.service_name} — {fmtMoney(a.price)} сум</div>
        {a.service_description && <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{a.service_description}</div>}
      </div>

      <div className="card">
        <div>📅 {a.formatted}</div>
      </div>

      {error && <div className="error">{error}</div>}

      {a.status === 'pending' && (
        <>
          <button className="btn-primary" disabled={busy} onClick={handleConfirm}>✅ Подтвердить</button>
          <button className="btn-secondary" disabled={busy} onClick={handleDecline}>❌ Отклонить</button>
        </>
      )}

      {a.status === 'confirmed' && !showAmountInput && (
        <button className="btn-primary" disabled={busy} onClick={() => setShowAmountInput(true)}>✅ Визит состоялся</button>
      )}

      {a.status === 'confirmed' && showAmountInput && (
        <div className="card">
          <div className="subtitle">Сумма оплаты (сум)</div>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="350000"
            style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text-primary)', marginBottom: 8 }}
          />
          <button className="btn-primary" disabled={busy} onClick={handleComplete}>Подтвердить оплату и начислить бонусы</button>
        </div>
      )}

      <button className="btn-secondary" onClick={onBack}>⬅️ К списку</button>
    </div>
  )
}

function AdminCalendar({ onBack, onOpen }) {
  const todayISO = new Date().toISOString().slice(0, 10)
  const [date, setDate] = useState(todayISO)
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setItems(null)
    api.adminCalendar(date).then(setItems).catch((e) => setError(e.message))
  }, [date])

  return (
    <div>
      <div className="title">Календарь</div>
      <input
        type="date"
        value={date}
        onChange={(e) => setDate(e.target.value)}
        style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid var(--border)', background: 'var(--bg-card)', color: 'var(--text-primary)', marginBottom: 12 }}
      />

      {error && <div className="error">{error}</div>}
      {!items && !error && <div className="loading">Загрузка…</div>}
      {items && items.length === 0 && <div className="empty">На эту дату записей нет</div>}

      {items && items.map((a) => (
        <button key={a.id} className="list-item" onClick={() => onOpen(a.id)}>
          <span>
            {a.start_time} · {a.doctor_name}<br />
            <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{a.patient_name} — {a.service_name}</span>
          </span>
          <span className="price">{STATUS_LABELS[a.status] || a.status}</span>
        </button>
      ))}

      <button className="btn-secondary" onClick={onBack}>⬅️ Назад</button>
    </div>
  )
}

function Referral({ onBack }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    api.getReferral().then(setData).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="error">{error}</div>
  if (!data) return <div className="loading">Загрузка…</div>

  function copyLink() {
    navigator.clipboard?.writeText(data.link)
    setCopied(true)
    tg?.HapticFeedback?.notificationOccurred('success')
    setTimeout(() => setCopied(false), 2000)
  }

  function shareLink() {
    const text = encodeURIComponent('Присоединяйся к Smile Clinic и получи бонус на первый визит! 🦷')
    tg?.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(data.link)}&text=${text}`)
  }

  return (
    <div>
      <div className="title">Пригласить друга</div>
      <div className="card">
        <div>🎁 Друг получает {fmtMoney(data.referred_bonus_default)} бонусов на первый визит</div>
        <div>💰 Вы получаете {fmtMoney(data.referrer_bonus_default)} бонусов, когда друг придёт</div>
      </div>

      <div className="card">
        <div className="subtitle">Ваша ссылка</div>
        <div style={{ wordBreak: 'break-all', fontSize: 13, marginBottom: 10 }}>{data.link}</div>
        <button className="btn-primary" onClick={shareLink}>Поделиться в Telegram</button>
        <button className="btn-secondary" onClick={copyLink}>{copied ? '✓ Скопировано' : 'Скопировать ссылку'}</button>
      </div>

      <div className="card">
        <div>Приглашено и получили бонус: {data.rewarded_count}</div>
        <div>Ждут первого визита: {data.pending_count}</div>
        <div>Всего заработано: {fmtMoney(data.total_earned)} бонусов</div>
      </div>

      <button className="btn-secondary" onClick={onBack}>⬅️ На главную</button>
    </div>
  )
}

// ---------- Level ----------

function Level({ onBack }) {
  const [me, setMe] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getMe().then(setMe).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="error">{error}</div>
  if (!me) return <div className="loading">Загрузка…</div>

  const remaining = me.next_level_threshold != null
    ? Math.max(0, me.next_level_threshold - me.lifetime_bonus_earned)
    : null

  return (
    <div>
      <div className="title">Мой уровень</div>

      <div className="balance-hero">
        <div className="label">Уровень</div>
        <div className="amount" style={{ fontSize: 26 }}>{me.level_name}</div>
        <div className="label">{me.bonus_percent}% бонусов с каждого визита</div>
      </div>

      <div className="card">
        <div>💰 Баланс: {fmtMoney(me.bonus_balance)} бонусов</div>
        <div>📈 Накоплено за всё время: {fmtMoney(me.lifetime_bonus_earned)}</div>
        {remaining !== null ? (
          <div>🎯 До следующего уровня: {fmtMoney(remaining)} бонусов</div>
        ) : (
          <div>🏆 Это максимальный уровень</div>
        )}
      </div>

      {me.benefits?.length > 0 && (
        <div className="card">
          <div className="subtitle">Ваши привилегии</div>
          {me.benefits.map((b, i) => <div key={i}>✓ {b}</div>)}
        </div>
      )}

      <button className="btn-secondary" onClick={onBack}>⬅️ На главную</button>
    </div>
  )
}

// ---------- Gifts ----------

function Gifts({ onBack }) {
  const [me, setMe] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getMe().then(setMe).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="error">{error}</div>
  if (!me) return <div className="loading">Загрузка…</div>

  return (
    <div>
      <div className="title">Бонусы и подарки</div>
      <div className="balance-hero">
        <div className="label">Ваш баланс</div>
        <div className="amount">{fmtMoney(me.bonus_balance)}</div>
      </div>
      <div className="empty">Каталог подарков и услуг за бонусы скоро появится здесь 🎁</div>
      <button className="btn-secondary" onClick={onBack}>⬅️ На главную</button>
    </div>
  )
}
