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
      <button className="list-item" onClick={() => onNavigate('referral')}>
        <span>👥 Пригласить друга</span>
        <span>›</span>
      </button>
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
              <span className="price">{d.specialization}</span>
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

// ---------- Referral ----------

function Referral({ onBack }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getReferral().then(setData).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="error">{error}</div>
  if (!data) return <div className="loading">Загрузка…</div>

  return (
    <div>
      <div className="title">Пригласить друга</div>
      <div className="card">
        <div>🎁 Друг получает {fmtMoney(data.referred_bonus_default)} бонусов на первый визит</div>
        <div>💰 Вы получаете {fmtMoney(data.referrer_bonus_default)} бонусов, когда друг придёт</div>
      </div>
      <div className="card">
        <div>Приглашено и получили бонус: {data.rewarded_count}</div>
        <div>Ждут первого визита: {data.pending_count}</div>
        <div>Всего заработано: {fmtMoney(data.total_earned)} бонусов</div>
      </div>
      <div className="subtitle">Ссылку для приглашения можно получить в чате бота, кнопка «Пригласить друга»</div>
      <button className="btn-secondary" onClick={onBack}>⬅️ На главную</button>
    </div>
  )
}
