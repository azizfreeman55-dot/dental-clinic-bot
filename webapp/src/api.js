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

  // Gifts
  getGifts: () => request('/api/gifts'),
  redeemGift: (id) => request(`/api/gifts/${id}/redeem`, { method: 'POST' }),
  getMyRedemptions: () => request('/api/gifts/my'),
  adminRedemptions: () => request('/api/admin/redemptions'),
  adminMarkRedemptionUsed: (id) => request(`/api/admin/redemptions/${id}/use`, { method: 'POST' }),
  adminRescheduleDates: (id) => request(`/api/admin/appointments/${id}/reschedule_dates`),
  adminRescheduleSlots: (id, date) => request(`/api/admin/appointments/${id}/reschedule_slots?date=${date}`),
  adminReschedule: (id, slotId) =>
    request(`/api/admin/appointments/${id}/reschedule`, {
      method: 'POST',
      body: JSON.stringify({ slot_id: slotId }),
    }),

  // Wheel
  getWheelPrizes: () => request('/api/wheel/prizes'),
  getWheelStatus: () => request('/api/wheel/status'),
  spinWheel: () => request('/api/wheel/spin', { method: 'POST' }),

  // Achievements
  getAchievements: () => request('/api/achievements'),

  // Missions
  getMissions: () => request('/api/missions'),

  // Profile
  updateProfile: (data) => request('/api/profile', { method: 'PUT', body: JSON.stringify(data) }),
};

export { tg };
