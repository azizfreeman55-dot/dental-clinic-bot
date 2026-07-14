const tg = window.Telegram?.WebApp;

function getInitData() {
  return tg?.initData || '';
}

async function request(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': getInitData(),
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || body.error || `Ошибка запроса: ${res.status}`);
  }

  return res.json();
}

export const api = {
  getMe: () => request('/api/me'),
  getServices: () => request('/api/services'),
  getDoctors: (serviceId) => request(`/api/doctors?service_id=${serviceId}`),
  getDates: (doctorId) => request(`/api/dates?doctor_id=${doctorId}`),
  getSlots: (doctorId, date) => request(`/api/slots?doctor_id=${doctorId}&date=${date}`),
  book: (serviceId, doctorId, slotId) =>
    request('/api/book', {
      method: 'POST',
      body: JSON.stringify({ service_id: serviceId, doctor_id: doctorId, slot_id: slotId }),
    }),
  getReferral: () => request('/api/referral'),

  // Admin
  adminStats: () => request('/api/admin/stats'),
  adminAppointments: (status) => request(`/api/admin/appointments?status=${status}`),
  adminAppointmentDetail: (id) => request(`/api/admin/appointments/${id}`),
  adminConfirm: (id) => request(`/api/admin/appointments/${id}/confirm`, { method: 'POST' }),
  adminDecline: (id) => request(`/api/admin/appointments/${id}/decline`, { method: 'POST' }),
  adminComplete: (id, amountPaid) =>
    request(`/api/admin/appointments/${id}/complete`, {
      method: 'POST',
      body: JSON.stringify({ amount_paid: amountPaid }),
    }),
  adminCalendar: (date) => request(`/api/admin/calendar?date=${date}`),
};

export { tg };
