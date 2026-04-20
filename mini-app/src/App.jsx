import React, { useState, useEffect } from 'react';
import { Search, Calendar, User, Star, Clock, MapPin, ChevronRight, CheckCircle2 } from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = '/api/v1'; // Served from the same host

function App() {
  const [view, setView] = useState('list'); // 'list', 'profile', 'booking', 'success', 'referral'
  const [barbers, setBarbers] = useState([]);
  const [selectedBarber, setSelectedBarber] = useState(null);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Initialize Telegram Web App
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.ready();
      tg.expand();
    }

    fetchBarbers();
  }, []);

  const fetchBarbers = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/barber/`);
      const data = response.data;
      setBarbers(data);
      
      // Feature: Single Barber Mode
      if (data.length === 1) {
        setSelectedBarber(data[0]);
        setView('profile');
      }
    } catch (error) {
      console.error("Error fetching barbers:", error);
      // Fallback data for demo
      const fallback = [
        { id: 1, full_name: "Azamat Sobirov", bio: "Yuqori sifatli erkaklar soch turmagi", rating: 4.9, location: "Toshkent, Chilonzor" },
        { id: 2, full_name: "Rustam Karimov", bio: "Soqol va soch bo'yicha mutaxassis", rating: 4.8, location: "Toshkent, Yunusobod" },
        { id: 3, full_name: "Javohir Ortiqov", bio: "Klassik va zamonaviy uslublar", rating: 5.0, location: "Toshkent, Mirobod" }
      ];
      setBarbers(fallback);
    } finally {
      setLoading(false);
    }
  };

  const syncUser = async () => {
    const tg = window.Telegram?.WebApp;
    if (tg?.initDataUnsafe?.user) {
      const tgUser = tg.initDataUnsafe.user;
      try {
        const response = await axios.post(`${API_BASE_URL}/client/sync`, {
          telegram_id: tgUser.id,
          first_name: tgUser.first_name,
          last_name: tgUser.last_name,
          username: tgUser.username,
          referred_by_id: tg.initDataUnsafe.start_param ? parseInt(tg.initDataUnsafe.start_param.replace('ref', '')) : null
        });
        // Fetch user data to get balance
        const userResponse = await axios.get(`${API_BASE_URL}/user/${response.data.id}`);
        setUser(userResponse.data);
      } catch (err) {
        console.error("Sync error:", err);
      }
    }
  };

  useEffect(() => {
    syncUser();
  }, []);

  const openProfile = (barber) => {
    setSelectedBarber(barber);
    setView('profile');
    window.scrollTo(0, 0);
  };

  const startBooking = () => {
    setView('booking');
  };

  const confirmBooking = () => {
    setView('success');
  };

  // Views
  if (view === 'list') {
    return (
      <div className="app-container">
        <header className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1>Cutzilla</h1>
          <button 
            onClick={() => setView('referral')}
            style={{ background: '#F5F5F7', border: 'none', borderRadius: '50%', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          >
            <User size={20} color="#007AFF" />
          </button>
        </header>
        <header className="header" style={{ paddingTop: 0 }}>
          <div style={{ marginTop: '15px', position: 'relative' }}>
            <Search size={20} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#86868B' }} />
            <input 
              type="text" 
              placeholder="Sartarosh qidirish..." 
              style={{ width: '100%', padding: '12px 12px 12px 40px', borderRadius: '12px', border: '1px solid #E5E5E7', backgroundColor: '#F5F5F7', fontSize: '15px' }}
            />
          </div>
        </header>

        <main style={{ marginTop: '20px' }}>
          <div style={{ padding: '0 20px', marginBottom: '20px' }}>
            <h2 style={{ fontSize: '20px', fontWeight: '600', margin: 0 }}>Eng yaxshi sartaroshlar</h2>
          </div>

          <div className="barber-grid">
            {loading ? (
              <p style={{ textAlign: 'center', padding: '20px' }}>Yuklanmoqda...</p>
            ) : (
              barbers.map((barber) => (
                <div key={barber.id} className="barber-card animate-fade-in" onClick={() => openProfile(barber)}>
                  <div className="barber-avatar" style={{ backgroundColor: '#E5F1FF', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <User size={40} color="#007AFF" />
                  </div>
                  <div className="barber-info" style={{ flex: 1 }}>
                    <h3>{barber.full_name}</h3>
                    <p>{barber.bio || "Tajribali sartarosh"}</p>
                    <div className="rating">
                      <Star size={14} fill="#FF9500" strokeWidth={0} />
                      <span>{barber.rating || "5.0"}</span>
                      <span style={{ color: '#86868B', marginLeft: '5px', fontWeight: '400' }}>(48+ baho)</span>
                    </div>
                  </div>
                  <ChevronRight size={20} color="#C7C7CC" />
                </div>
              ))
            )}
          </div>
        </main>
      </div>
    );
  }

  if (view === 'profile') {
    return (
      <div className="app-container">
        <div style={{ position: 'relative' }}>
          <div style={{ height: '250px', backgroundColor: '#007AFF', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
             <User size={100} color="white" opacity={0.3} />
          </div>
          <button 
            onClick={() => setView('list')}
            style={{ position: 'absolute', top: '20px', left: '20px', background: 'rgba(255,255,255,0.2)', border: 'none', borderRadius: '50%', width: '40px', height: '40px', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', backdropFilter: 'blur(5px)' }}
          >
            <ChevronRight size={24} style={{ transform: 'rotate(180deg)' }} />
          </button>
        </div>

        <div style={{ padding: '20px', marginTop: '-40px', background: 'white', borderRadius: '40px 40px 0 0', flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <h2 style={{ margin: 0, fontSize: '28px' }}>{selectedBarber.full_name}</h2>
              <p style={{ color: '#86868B', marginTop: '5px', display: 'flex', alignItems: 'center', gap: '5px' }}>
                <MapPin size={16} /> {selectedBarber.location || "Toshkent"}
              </p>
            </div>
            <div className="rating" style={{ fontSize: '18px', padding: '8px 12px', background: '#FFF9E5', borderRadius: '12px' }}>
              <Star size={20} fill="#FF9500" strokeWidth={0} />
              <span>{selectedBarber.rating || "5.0"}</span>
            </div>
          </div>

          <div style={{ marginTop: '30px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '600' }}>Xizmatlar</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '15px' }}>
              {[
                { name: "Soch kesish (Klassik)", price: "50,000 so'm", time: "45 daqiqa" },
                { name: "Soch va soqol", price: "80,000 so'm", time: "60 daqiqa" },
                { name: "Bolalar uchun", price: "40,000 so'm", time: "30 daqiqa" }
              ].map((s, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '15px', border: '1px solid #E5E5E7', borderRadius: '16px' }}>
                  <div>
                    <div style={{ fontWeight: '600' }}>{s.name}</div>
                    <div style={{ fontSize: '13px', color: '#86868B', marginTop: '4px' }}><Clock size={12} style={{ verticalAlign: 'middle', marginRight: '4px' }}/>{s.time}</div>
                  </div>
                  <div style={{ color: '#007AFF', fontWeight: '700' }}>{s.price}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, padding: '20px', background: 'white', borderTop: '1px solid #E5E5E7' }}>
          <button className="btn-primary" onClick={startBooking}>Navbatga yozilish</button>
        </div>
      </div>
    );
  }

  if (view === 'booking') {
    return (
      <div className="app-container">
        <header className="header" style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
           <button 
            onClick={() => setView('profile')}
            style={{ background: 'none', border: 'none', color: '#007AFF', padding: 0 }}
          >
            <ChevronRight size={24} style={{ transform: 'rotate(180deg)' }} />
          </button>
          <h1 style={{ fontSize: '20px' }}>Vaqtni tanlang</h1>
        </header>

        <div style={{ padding: '20px' }}>
           <div style={{ marginBottom: '25px' }}>
             <h3 style={{ fontSize: '18px', marginBottom: '15px' }}>Kun</h3>
             <div style={{ display: 'flex', gap: '10px', overflowX: 'auto', paddingBottom: '10px' }}>
               {['Dush', 'Sesh', 'Chor', 'Pay', 'Jum', 'Shan'].map((day, i) => (
                 <div key={i} style={{ minWidth: '65px', padding: '15px 10px', borderRadius: '16px', border: i === 0 ? '2px solid #007AFF' : '1px solid #E5E5E7', textAlign: 'center', background: i === 0 ? '#E5F1FF' : 'white' }}>
                   <div style={{ fontSize: '13px', color: i === 0 ? '#007AFF' : '#86868B' }}>{day}</div>
                   <div style={{ fontSize: '18px', fontWeight: '700', marginTop: '5px', color: i === 0 ? '#007AFF' : '#1D1D1F' }}>{10+i}</div>
                 </div>
               ))}
             </div>
           </div>

           <div>
             <h3 style={{ fontSize: '18px', marginBottom: '15px' }}>Bo'sh vaqtlar</h3>
             <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
               {['09:00', '10:00', '11:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00'].map((time, i) => (
                 <div 
                  key={i} 
                  onClick={confirmBooking}
                  style={{ padding: '15px 10px', borderRadius: '12px', border: '1px solid #E5E5E7', textAlign: 'center', fontSize: '15px', fontWeight: '500' }}
                >
                   {time}
                 </div>
               ))}
             </div>
           </div>
        </div>
      </div>
    );
  }

  if (view === 'success') {
    return (
      <div className="app-container" style={{ justifyContent: 'center', alignItems: 'center', textAlign: 'center', padding: '40px' }}>
        <div style={{ marginBottom: '30px' }}>
          <CheckCircle2 size={100} color="#34C759" strokeWidth={1.5} />
        </div>
        <h2 style={{ fontSize: '28px', marginBottom: '10px' }}>Muvaffaqiyatli!</h2>
        <p style={{ color: '#86868B', fontSize: '17px', lineHeight: '1.5' }}>
          Siz {selectedBarber?.full_name} qabuliga muvaffaqiyatli yozildingiz.
          <br />Tasdiqlash xabari bot orqali yuboriladi.
        </p>
        <div style={{ width: '100%', marginTop: '40px' }}>
          <button className="btn-primary" onClick={() => setView(barbers.length === 1 ? 'profile' : 'list')}>Asosiy menyuga qaytish</button>
        </div>
      </div>
    );
  }

  if (view === 'referral') {
    const referralLink = `https://t.me/CutzillaBot?start=ref${user?.telegram_id || ''}`;
    
    const shareReferral = () => {
      const tg = window.Telegram?.WebApp;
      if (tg) {
        tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(referralLink)}&text=${encodeURIComponent("Do'stim, yanada chiroyli bo'lishing uchun ushbu sartaroshni tavsiya qilaman! Ro'yxatdan o't va chegirmalarga ega bo'l.")}`);
      } else {
        navigator.clipboard.writeText(referralLink);
        alert("Havola nusxalandi!");
      }
    };

    return (
      <div className="app-container">
        <header className="header" style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
           <button 
            onClick={() => setView(barbers.length === 1 ? 'profile' : 'list')}
            style={{ background: 'none', border: 'none', color: '#007AFF', padding: 0 }}
          >
            <ChevronRight size={24} style={{ transform: 'rotate(180deg)' }} />
          </button>
          <h1 style={{ fontSize: '20px' }}>Shaxsiy kabinet</h1>
        </header>

        <div style={{ padding: '20px' }}>
          <div style={{ background: 'linear-gradient(135deg, #007AFF 0%, #0056B3 100%)', borderRadius: '24px', padding: '25px', color: 'white', marginBottom: '30px' }}>
            <div style={{ fontSize: '15px', opacity: 0.8 }}>Sizning balansingiz</div>
            <div style={{ fontSize: '32px', fontWeight: '700', marginTop: '5px' }}>{user?.balance || 0} <span style={{ fontSize: '18px', fontWeight: '400' }}>so'm</span></div>
          </div>

          <div style={{ background: '#F5F5F7', borderRadius: '24px', padding: '25px', textAlign: 'center' }}>
             <Star size={40} color="#FF9500" style={{ marginBottom: '15px' }} />
             <h3 style={{ fontSize: '20px', fontWeight: '600' }}>Do'stlaringizni taklif qiling</h3>
             <p style={{ color: '#86868B', marginTop: '10px', lineHeight: '1.5' }}>
               Har bir taklif qilingan do'stingizning birinchi tashrifidan so'ng sizga xizmat haqining bir qismi bonus sifatida beriladi!
             </p>
             <button 
              className="btn-primary" 
              style={{ marginTop: '20px' }}
              onClick={shareReferral}
             >
               Havolani ulashish
             </button>
          </div>
        </div>
      </div>
    );
  }
}

export default App;
