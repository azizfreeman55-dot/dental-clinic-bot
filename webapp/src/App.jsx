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
      {screen === 'profile' && <Profile onBack={() => setScreen('home')} />}
      {screen === 'referral' && <Referral onBack={() => setScreen('home')} />}
      {screen === 'level' && <Level onBack={() => setScreen('home')} />}
      {screen === 'gifts' && <Gifts onBack={() => setScreen('home')} />}
      {screen === 'wheel' && <Wheel onBack={() => setScreen('home')} />}
      {screen === 'achievements' && <Achievements onBack={() => setScreen('home')} />}
      {screen === 'missions' && <Missions onBack={() => setScreen('home')} />}
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
      <button className="list-item" onClick={() => onNavigate('profile')}>
        <span>👤 Мой профиль{!me.profile_complete ? ' ⚠️' : ''}</span>
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
      <button className="list-item" onClick={() => onNavigate('wheel')}>
        <span>🎰 Колесо фортуны</span>
        <span>›</span>
      </button>
      <button className="list-item" onClick={() => onNavigate('achievements')}>
        <span>🏆 Достижения</span>
        <span>›</span>
      </button>
      <button className="list-item" onClick={() => onNavigate('missions')}>
        <span>🎯 Миссии месяца</span>
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

// ---------- Profile ----------

function Profile({ onBack }) {
  const [me, setMe] = useState(null)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [birthDate, setBirthDate] = useState('')
  const [gender, setGender] = useState('')

  useEffect(() => {
    api.getMe().then((data) => {
      setMe(data)
      setFullName(data.full_name || '')
      setPhone(data.phone || '')
      setBirthDate(data.birth_date || '')
      setGender(data.gender || '')
    }).catch((e) => setError(e.message))
  }, [])

  async function handleSave() {
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      await api.updateProfile({
        full_name: fullName,
        phone,
        birth_date: birthDate,
        gender,
      })
      setSaved(true)
      tg?.HapticFeedback?.notificationOccurred('success')
      setTimeout(() => setSaved(false), 2500)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  if (error && !me) return <div className="error">{error}</div>
  if (!me) return <div className="loading">Загрузка…</div>

  const inputStyle = {
    width: '100%', padding: 12, borderRadius: 10, border: '1px solid var(--border)',
    background: 'var(--bg-card)', color: 'var(--text-primary)', marginBottom: 12, fontSize: 15,
  }

  return (
    <div>
      <div className="title">Мой профиль</div>
      <div className="subtitle">Эти данные помогают клинике связаться с вами и поздравить с днём рождения 🎂</div>

      <div className="card">
        <label style={{ fontSize: 13, color: 'var(--text-secondary)' }}>ФИО</label>
        <input
          style={inputStyle}
          type="text"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="Иванов Иван Иванович"
        />

        <label style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Телефон</label>
        <input
          style={inputStyle}
          type="tel"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="+998 90 123 45 67"
        />

        <label style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Дата рождения</label>
        <input
          style={inputStyle}
          type="date"
          value={birthDate}
          onChange={(e) => setBirthDate(e.target.value)}
        />

        <label style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Пол</label>
        <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', marginBottom: 4 }}>
          <div
            className="chip"
            onClick={() => setGender('male')}
            style={gender === 'male' ? { background: 'var(--accent)', color: 'white' } : {}}
          >
            👨 Мужской
          </div>
          <div
            className="chip"
            onClick={() => setGender('female')}
            style={gender === 'female' ? { background: 'var(--accent)', color: 'white' } : {}}
          >
            👩 Женский
          </div>
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {saved && <div className="card" style={{ borderColor: 'var(--accent-lime)', textAlign: 'center' }}>✓ Сохранено</div>}

      <button className="btn-primary" disabled={saving} onClick={handleSave}>
        {saving ? 'Сохраняем…' : 'Сохранить'}
      </button>
      <button className="btn-secondary" onClick={onBack}>⬅️ На главную</button>
    </div>
  )
}

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

// ---------- Wheel of Fortune ----------

function buildConicGradient(prizes) {
  const slice = 360 / prizes.length
  const stops = prizes.map((p, i) => `${p.color} ${i * slice}deg ${(i + 1) * slice}deg`)
  return `conic-gradient(${stops.join(', ')})`
}

function Wheel({ onBack }) {
  const [prizes, setPrizes] = useState(null)
  const [spinsAvailable, setSpinsAvailable] = useState(0)
  const [error, setError] = useState(null)
  const [rotation, setRotation] = useState(0)
  const [spinning, setSpinning] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => {
    api.getWheelPrizes().then(setPrizes).catch((e) => setError(e.message))
    api.getWheelStatus().then((s) => setSpinsAvailable(s.spins_available)).catch((e) => setError(e.message))
  }, [])

  async function handleSpin() {
    if (spinning || spinsAvailable <= 0) return
    setSpinning(true)
    setResult(null)
    setError(null)

    try {
      const res = await api.spinWheel()
      const idx = prizes.findIndex((p) => p.id === res.prize_id)
      const slice = 360 / prizes.length
      const center = idx * slice + slice / 2
      const jitter = (Math.random() - 0.5) * (slice * 0.6)
      const targetMod = (360 - center + jitter + 360) % 360
      const extraSpins = 5

      setRotation((prev) => {
        const prevMod = prev % 360
        let delta = targetMod - prevMod
        if (delta < 0) delta += 360
        return prev + delta + extraSpins * 360
      })

      setTimeout(() => {
        setResult(res)
        setSpinsAvailable((s) => s - 1)
        setSpinning(false)
        tg?.HapticFeedback?.notificationOccurred(res.bonus_amount > 0 ? 'success' : 'warning')
      }, 4000)
    } catch (e) {
      setSpinning(false)
      setError(e.message.includes('409') ? 'Нет доступных вращений' : e.message)
    }
  }

  if (error && !prizes) return <div className="error">{error}</div>
  if (!prizes) return <div className="loading">Загрузка…</div>

  const slice = 360 / prizes.length
  const radius = 110

  return (
    <div>
      <div className="title">Колесо фортуны</div>
      <div className="subtitle">Доступно вращений: {spinsAvailable}</div>

      <div style={{ display: 'flex', justifyContent: 'center', margin: '20px 0', position: 'relative' }}>
        <div style={{
          position: 'absolute', top: -10, left: '50%', transform: 'translateX(-50%)',
          width: 0, height: 0, borderLeft: '14px solid transparent', borderRight: '14px solid transparent',
          borderTop: '24px solid var(--accent-lime)', zIndex: 3,
          filter: 'drop-shadow(0 2px 3px rgba(0,0,0,0.4))',
        }} />
        <div
          style={{
            width: 280, height: 280, borderRadius: '50%',
            background: buildConicGradient(prizes),
            border: '6px solid var(--bg-card)',
            outline: '2px solid var(--border)',
            position: 'relative',
            boxShadow: '0 8px 24px rgba(0,0,0,0.5), inset 0 0 20px rgba(0,0,0,0.25)',
            transform: `rotate(${rotation}deg)`,
            transition: spinning ? 'transform 4s cubic-bezier(0.17, 0.67, 0.12, 0.99)' : 'none',
          }}
        >
          {/* тонкие разделители между секторами */}
          <div style={{
            position: 'absolute', inset: 0, borderRadius: '50%',
            background: `repeating-conic-gradient(from 0deg, rgba(255,255,255,0.35) 0deg 1.5deg, transparent 1.5deg ${slice}deg)`,
            pointerEvents: 'none',
          }} />

          {prizes.map((p, i) => {
            const center = i * slice + slice / 2
            const cssRotate = center - 90 // conic-gradient 0°=верх, CSS rotate(0)=локальная ось X вправо — компенсируем сдвиг
            return (
              <div
                key={p.id}
                style={{
                  position: 'absolute', top: '50%', left: '50%',
                  transform: `rotate(${cssRotate}deg)`,
                  transformOrigin: '0 0',
                  width: radius,
                }}
              >
                <span style={{
                  position: 'absolute', left: radius - 60, top: -8,
                  transform: `rotate(${-cssRotate}deg)`,
                  fontSize: 12, fontWeight: 800, color: 'white', width: 65, textAlign: 'center',
                  textShadow: '0 1px 3px rgba(0,0,0,0.6)',
                  letterSpacing: 0.2,
                }}>
                  {p.name}
                </span>
              </div>
            )
          })}
        </div>

        {/* декоративная втулка в центре */}
        <div style={{
          position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
          width: 52, height: 52, borderRadius: '50%',
          background: 'radial-gradient(circle at 35% 30%, #2a3f5c, var(--bg-card) 70%)',
          border: '3px solid var(--accent-lime)',
          boxShadow: '0 4px 10px rgba(0,0,0,0.5)',
          zIndex: 2,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 20,
        }}>
          🦷
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {result && (
        <div className="card" style={{ textAlign: 'center', borderColor: result.bonus_amount > 0 ? 'var(--accent-lime)' : 'var(--border)' }}>
          {result.bonus_amount > 0 ? (
            <>🎉 Поздравляем! Вы выиграли <b>{fmtMoney(result.bonus_amount)}</b> бонусов</>
          ) : (
            <>Не повезло в этот раз, попробуйте после следующего визита!</>
          )}
        </div>
      )}

      <button className="btn-primary" disabled={spinning || spinsAvailable <= 0} onClick={handleSpin}>
        {spinning ? 'Крутится…' : spinsAvailable > 0 ? 'Крутить' : 'Нет вращений'}
      </button>

      {spinsAvailable <= 0 && (
        <div className="subtitle" style={{ textAlign: 'center', marginTop: 8 }}>
          Новое вращение начисляется за каждый завершённый визит
        </div>
      )}

      <button className="btn-secondary" onClick={onBack}>⬅️ На главную</button>
    </div>
  )
}

const STATUS_LABELS = {
  pending: 'Ожидает подтверждения',
  confirmed: 'Подтверждена',
  completed: 'Завершена',
  cancelled_by_patient: 'Отменена пациентом',
  cancelled_by_admin: 'Отклонена админом',
  awaiting_reschedule: 'Ждём ответ на перенос',
}

// ---------- Achievements ----------

function Achievements({ onBack }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getAchievements().then(setItems).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="error">{error}</div>
  if (!items) return <div className="loading">Загрузка…</div>

  const earnedCount = items.filter((a) => a.earned).length

  return (
    <div>
      <div className="title">Достижения</div>
      <div className="subtitle">Получено {earnedCount} из {items.length}</div>

      {items.map((a) => (
        <div
          key={a.id}
          className="card"
          style={{
            display: 'flex', alignItems: 'center', gap: 14,
            opacity: a.earned ? 1 : 0.45,
          }}
        >
          <div style={{
            fontSize: 32, width: 52, height: 52, borderRadius: '50%',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: a.earned ? 'linear-gradient(135deg, var(--accent), #1a4fc4)' : 'var(--bg)',
            border: '1px solid var(--border)', flexShrink: 0,
          }}>
            {a.icon}
          </div>
          <div>
            <div style={{ fontWeight: 700 }}>{a.name}</div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{a.description}</div>
            {a.earned && (
              <div style={{ fontSize: 11, color: 'var(--accent-lime)', marginTop: 2 }}>
                ✓ Получено {new Date(a.earned_at).toLocaleDateString('ru-RU')}
              </div>
            )}
          </div>
        </div>
      ))}

      <button className="btn-secondary" onClick={onBack}>⬅️ На главную</button>
    </div>
  )
}

// ---------- Missions ----------

function Missions({ onBack }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getMissions().then(setItems).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="error">{error}</div>
  if (!items) return <div className="loading">Загрузка…</div>

  return (
    <div>
      <div className="title">Миссии месяца</div>
      <div className="subtitle">Выполняйте задания и получайте бонусы</div>

      {items.length === 0 && <div className="empty">Пока нет активных миссий</div>}

      {items.map((m) => {
        const pct = Math.round((m.progress / m.target_count) * 100)
        return (
          <div key={m.id} className="card" style={{ opacity: m.completed ? 0.7 : 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontWeight: 700 }}>{m.completed ? '✅ ' : '🎯 '}{m.name}</div>
              <span className="price">+{fmtMoney(m.reward_bonus)}</span>
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', margin: '6px 0' }}>{m.description}</div>

            <div style={{ background: 'var(--bg)', borderRadius: 8, height: 8, overflow: 'hidden', marginTop: 8 }}>
              <div style={{
                width: `${pct}%`, height: '100%',
                background: m.completed ? 'var(--accent-lime)' : 'var(--accent)',
                transition: 'width 0.3s',
              }} />
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
              {m.progress} из {m.target_count}
              {m.period === 'monthly' && !m.completed ? ' в этом месяце' : ''}
            </div>
          </div>
        )
      })}

      <button className="btn-secondary" onClick={onBack}>⬅️ На главную</button>
    </div>
  )
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
          onOpenRedemptions={() => setView('redemptions')}
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
      {view === 'redemptions' && (
        <AdminRedemptions onBack={() => setView('home')} />
      )}
    </div>
  )
}

function AdminHome({ onBack, onOpenList, onOpenCalendar, onOpenRedemptions }) {
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
      <button className="list-item" onClick={onOpenRedemptions}>
        <span>🎁 Погашение подарков</span><span>›</span>
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
  const [reschedStep, setReschedStep] = useState(null) // null | 'dates' | 'slots'
  const [reschedDates, setReschedDates] = useState(null)
  const [reschedSlots, setReschedSlots] = useState(null)
  const [reschedDate, setReschedDate] = useState(null)

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

  async function startReschedule() {
    setReschedStep('dates')
    setReschedDates(null)
    try {
      const dates = await api.adminRescheduleDates(id)
      setReschedDates(dates)
    } catch (e) { setError(e.message) }
  }

  async function pickReschedDate(d) {
    setReschedDate(d)
    setReschedStep('slots')
    setReschedSlots(null)
    try {
      const slots = await api.adminRescheduleSlots(id, d)
      setReschedSlots(slots)
    } catch (e) { setError(e.message) }
  }

  async function pickReschedSlot(slotId) {
    setBusy(true)
    try {
      await api.adminReschedule(id, slotId)
      onDone()
    } catch (e) {
      setError(e.message.includes('409') ? 'Этот слот уже заняли, выберите другой' : e.message)
    } finally {
      setBusy(false)
    }
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

      {a.status === 'pending' && !reschedStep && (
        <>
          <button className="btn-primary" disabled={busy} onClick={handleConfirm}>✅ Подтвердить</button>
          <button className="btn-secondary" disabled={busy} onClick={startReschedule}>🔄 Предложить другое время</button>
          <button className="btn-secondary" disabled={busy} onClick={handleDecline}>❌ Отклонить</button>
        </>
      )}

      {reschedStep === 'dates' && (
        <div className="card">
          <div className="subtitle">Выберите новую дату</div>
          {!reschedDates && <div className="loading">Загрузка…</div>}
          {reschedDates && reschedDates.length === 0 && <div className="empty">Нет свободных дат у этого врача</div>}
          <div className="grid">
            {reschedDates && reschedDates.map((d) => (
              <div key={d} className="chip" onClick={() => pickReschedDate(d)}>{fmtDate(d)}</div>
            ))}
          </div>
          <button className="btn-secondary" onClick={() => setReschedStep(null)}>⬅️ Отмена</button>
        </div>
      )}

      {reschedStep === 'slots' && (
        <div className="card">
          <div className="subtitle">Выберите время на {fmtDate(reschedDate)}</div>
          {!reschedSlots && <div className="loading">Загрузка…</div>}
          {reschedSlots && reschedSlots.length === 0 && <div className="empty">На эту дату свободного времени нет</div>}
          <div className="grid cols-4">
            {reschedSlots && reschedSlots.map((s) => (
              <div key={s.id} className="chip" onClick={() => !busy && pickReschedSlot(s.id)}>{s.start_time}</div>
            ))}
          </div>
          <button className="btn-secondary" onClick={() => setReschedStep('dates')}>⬅️ Назад к датам</button>
        </div>
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

function AdminRedemptions({ onBack }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [busyId, setBusyId] = useState(null)

  function load() {
    api.adminRedemptions().then(setItems).catch((e) => setError(e.message))
  }

  useEffect(() => { load() }, [])

  async function handleMarkUsed(id) {
    setBusyId(id)
    try {
      await api.adminMarkRedemptionUsed(id)
      load()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div>
      <div className="title">Погашение подарков</div>
      {error && <div className="error">{error}</div>}
      {!items && !error && <div className="loading">Загрузка…</div>}
      {items && items.length === 0 && <div className="empty">Нет подарков, ожидающих выдачи</div>}

      {items && items.map((r) => (
        <div key={r.id} className="card">
          <div style={{ fontWeight: 600 }}>{r.gift_name}</div>
          <div>👤 {r.patient_name}{r.phone ? ` · ${r.phone}` : ''}</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Код: №{r.id} · {fmtMoney(r.cost_bonuses)} бонусов</div>
          <button className="btn-primary" disabled={busyId === r.id} onClick={() => handleMarkUsed(r.id)} style={{ marginTop: 8 }}>
            {busyId === r.id ? 'Отмечаем…' : '✅ Выдано, отметить использованным'}
          </button>
        </div>
      ))}

      <button className="btn-secondary" onClick={onBack}>⬅️ Назад</button>
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
    const text = encodeURIComponent('Присоединяйся к Стоматологии Жемчужина и получи бонус на первый визит! 🦷')
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
  const [gifts, setGifts] = useState(null)
  const [myRedemptions, setMyRedemptions] = useState(null)
  const [tab, setTab] = useState('catalog') // catalog | mine
  const [error, setError] = useState(null)
  const [busyId, setBusyId] = useState(null)
  const [confirmGift, setConfirmGift] = useState(null)

  function loadAll() {
    api.getMe().then(setMe).catch((e) => setError(e.message))
    api.getGifts().then(setGifts).catch((e) => setError(e.message))
    api.getMyRedemptions().then(setMyRedemptions).catch((e) => setError(e.message))
  }

  useEffect(() => { loadAll() }, [])

  async function doRedeem(gift) {
    setBusyId(gift.id)
    setError(null)
    try {
      await api.redeemGift(gift.id)
      tg?.HapticFeedback?.notificationOccurred('success')
      setConfirmGift(null)
      loadAll()
      setTab('mine')
    } catch (e) {
      setError(e.message.includes('409') || e.message.includes('insufficient') ? 'Недостаточно бонусов для этого подарка' : e.message)
    } finally {
      setBusyId(null)
    }
  }

  if (error && !gifts) return <div className="error">{error}</div>
  if (!me || !gifts || !myRedemptions) return <div className="loading">Загрузка…</div>

  return (
    <div>
      <div className="title">Бонусы и подарки</div>
      <div className="balance-hero">
        <div className="label">Ваш баланс</div>
        <div className="amount">{fmtMoney(me.bonus_balance)}</div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', marginBottom: 12 }}>
        <div className="chip" onClick={() => setTab('catalog')} style={tab === 'catalog' ? { background: 'var(--accent)', color: 'white' } : {}}>
          Каталог
        </div>
        <div className="chip" onClick={() => setTab('mine')} style={tab === 'mine' ? { background: 'var(--accent)', color: 'white' } : {}}>
          Мои подарки {myRedemptions.length > 0 ? `(${myRedemptions.length})` : ''}
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {tab === 'catalog' && (
        <>
          {gifts.length === 0 && <div className="empty">Каталог пока пуст</div>}
          {gifts.map((g) => {
            const canAfford = me.bonus_balance >= g.cost_bonuses
            return (
              <div key={g.id} className="card">
                <div style={{ fontWeight: 600 }}>{g.name}</div>
                {g.description && <div style={{ color: 'var(--text-secondary)', fontSize: 13, marginTop: 4 }}>{g.description}</div>}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 }}>
                  <span className="price">{fmtMoney(g.cost_bonuses)} бонусов</span>
                  <button
                    className="btn-secondary"
                    style={{ width: 'auto', margin: 0, padding: '8px 16px', opacity: canAfford ? 1 : 0.5 }}
                    disabled={!canAfford || busyId === g.id}
                    onClick={() => setConfirmGift(g)}
                  >
                    {canAfford ? 'Обменять' : 'Не хватает бонусов'}
                  </button>
                </div>
              </div>
            )
          })}
        </>
      )}

      {tab === 'mine' && (
        <>
          {myRedemptions.length === 0 && <div className="empty">Вы ещё ничего не обменивали</div>}
          {myRedemptions.map((r) => (
            <div key={r.id} className="card">
              <div style={{ fontWeight: 600 }}>{r.gift_name}</div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Код погашения: №{r.id}</div>
              <div style={{ marginTop: 6 }}>
                {r.status === 'pending' && <span style={{ color: 'var(--accent-lime)' }}>🟢 Готово к использованию — покажите администратору</span>}
                {r.status === 'used' && <span style={{ color: 'var(--text-secondary)' }}>✓ Использовано</span>}
              </div>
            </div>
          ))}
        </>
      )}

      {confirmGift && (
        <div className="card" style={{ borderColor: 'var(--accent)' }}>
          <div>Обменять <b>{fmtMoney(confirmGift.cost_bonuses)}</b> бонусов на «{confirmGift.name}»?</div>
          <button className="btn-primary" disabled={busyId === confirmGift.id} onClick={() => doRedeem(confirmGift)}>
            {busyId === confirmGift.id ? 'Обмениваем…' : 'Подтвердить обмен'}
          </button>
          <button className="btn-secondary" onClick={() => setConfirmGift(null)}>Отмена</button>
        </div>
      )}

      <button className="btn-secondary" onClick={onBack}>⬅️ На главную</button>
    </div>
  )
}
