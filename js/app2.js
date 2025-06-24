function App() {
  const [loading, setLoading] = React.useState(true);
  const [games, setGames] = React.useState([]);
  const [keysDB, setKeysDB] = React.useState({});
  const [usersDB, setUsersDB] = React.useState({});

  const [currentUser, setCurrentUser] = React.useState(null);

  const [showLoginModal, setShowLoginModal] = React.useState(false);
  const [showGameDetails, setShowGameDetails] = React.useState(null);
  const [showProfileModal, setShowProfileModal] = React.useState(false);

  const telegramLink = "https://t.me/moiseishop24bot";

  React.useEffect(() => {
    const fetchData = async () => {
      try {
        const localUsers = JSON.parse(localStorage.getItem('gamestore_users') || '{}');
        const localKeys = localStorage.getItem('gamestore_keys');

        const [gamesData, initialKeys, freshUsersData] = await Promise.all([
          fetch('data/games.json').then(res => res.json()),
          localKeys ? Promise.resolve(JSON.parse(localKeys)) : fetch('data/keys.json').then(res => res.json()),
          fetch('data/users.json').then(res => res.json())
        ]);

        const updatedUsers = { ...localUsers };
        Object.keys(freshUsersData).forEach(email => {
          if (!updatedUsers[email]) {
            updatedUsers[email] = freshUsersData[email];
          }
        });

        setGames(gamesData);
        setKeysDB(initialKeys);
        setUsersDB(updatedUsers);

        if (!localKeys) localStorage.setItem('gamestore_keys', JSON.stringify(initialKeys));
        localStorage.setItem('gamestore_users', JSON.stringify(updatedUsers));

      } catch (error) {
        console.error("Помилка завантаження даних:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const saveUsersDB = (updatedUsers) => {
    localStorage.setItem('gamestore_users', JSON.stringify(updatedUsers));
    setUsersDB(updatedUsers);
  };

  const saveKeysDB = (updatedKeys) => {
    localStorage.setItem('gamestore_keys', JSON.stringify(updatedKeys));
    setKeysDB(updatedKeys);
  };

  const handleLogin = (user) => setCurrentUser(user);
  const handleLogout = () => setCurrentUser(null);

  const handlePurchase = (updatedUser) => {
    setCurrentUser({...updatedUser});
    const newUsersDB = {...usersDB, [updatedUser.email]: updatedUser};
    saveUsersDB(newUsersDB);
  };

  const handleClearStorage = () => {
    if (confirm('Оновити данні')) {
      localStorage.clear();
      window.location.reload();
    }
  };

  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center" style={{ height: '100vh' }}>
        <div className="spinner-border text-light" role="status">
          <span className="visually-hidden">Завантаження...</span>
        </div>
      </div>
    );
  }

  return (
    <div>
      <nav className="navbar navbar-expand-lg navbar-light sticky-top">
        <div className="container">
          <a className="navbar-brand fw-bold" href="#">
            <img src="images/moisey.png" alt="Logo" style={{width: '40px', height: '40px', marginRight: '8px'}} />
            Шишки Моісея
          </a>
          <div className="d-flex align-items-center">
            {currentUser && <span className="me-3 balance-display">{currentUser.balance} ₴</span>}
            <a href={telegramLink} target="_blank" className="btn btn-telegram me-2">
              <i className="fab fa-telegram-plane me-1"></i> Telegram
            </a>
            <button className="btn btn-warning me-2" onClick={handleClearStorage} title="Очистити localStorage">
              <i className="fas fa-trash me-1"></i>Оновлення
            </button>
            {currentUser ? (
              <>
                <button className="btn btn-outline-secondary me-2" onClick={() => setShowProfileModal(true)}>
                  <i className="fas fa-user me-1"></i> {currentUser.name}
                </button>
                <button className="btn btn-outline-danger" onClick={handleLogout}>Вийти</button>
              </>
            ) : (
              <button className="btn btn-primary" onClick={() => setShowLoginModal(true)}>
                Увійти
              </button>
            )}
          </div>
        </div>
      </nav>

      <div className="container mt-4">
        <div className="row g-4">
          {games.map(game => (
            <div key={game.id} className="col-lg-3 col-md-4 col-sm-6 animate-fade-in">
              <div className="card h-100 game-card">
                <img src={game.image} className="card-img-top" alt={game.title} />
                <div className="card-body d-flex flex-column">
                  <h5 className="card-title">{game.title}</h5>
                  {game.discount > 0 && <span className="badge bg-danger align-self-start">-{game.discount}%</span>}
                  <p className="card-text mt-2"><span className="badge bg-secondary">{game.platform}</span></p>
                  <div className="mt-auto d-flex justify-content-between align-items-center">
                    <span className="fw-bold fs-5 text-primary">{Math.round(game.price * (1 - game.discount / 100))} ₴</span>
                    <button className="btn btn-primary" onClick={() => setShowGameDetails(game)}>
                      Деталі
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <LoginModal show={showLoginModal} onClose={() => setShowLoginModal(false)} onLogin={handleLogin} usersDB={usersDB} />
      <GameDetailsModal game={showGameDetails} show={!!showGameDetails} onClose={() => setShowGameDetails(null)} user={currentUser} onPurchase={handlePurchase} keysDB={keysDB} saveKeysDB={saveKeysDB} usersDB={usersDB} saveUsersDB={saveUsersDB} />
      <ProfileModal user={currentUser} show={showProfileModal} onClose={() => setShowProfileModal(false)} />
    </div>
  );
}

function LoginModal({ show, onClose, onLogin, usersDB }) {
  const [formData, setFormData] = React.useState({ email: '', password: '' });
  const [errors, setErrors] = React.useState({});
  const [isLoading, setIsLoading] = React.useState(false);

  const validateForm = () => {
    const newErrors = {};
    if (!formData.email.trim() || !/\S+@\S+\.\S+/.test(formData.email)) newErrors.email = 'Невірний формат email';
    if (!formData.password.trim()) newErrors.password = 'Пароль обов\'язковий';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;
    setIsLoading(true);
    await new Promise(resolve => setTimeout(resolve, 500));

    const user = usersDB[formData.email];
    if (user && user.password === formData.password) {
      onLogin(user);
      onClose();
      setFormData({ email: '', password: '' });
      setErrors({});
    } else {
      setErrors({ general: 'Невірний email або пароль' });
    }
    setIsLoading(false);
  };

  if (!show) return null;
  return (
    <div className="modal show d-block" style={{backgroundColor: 'rgba(0,0,0,0.5)'}}>
      <div className="modal-dialog modal-dialog-centered">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">Вхід</h5>
            <button type="button" className="btn-close" onClick={onClose}></button>
          </div>
          <div className="modal-body">
            <form onSubmit={handleSubmit}>
              {errors.general && <div className="alert alert-danger">{errors.general}</div>}
              <div className="mb-3">
                <label className="form-label">Email</label>
                <input type="email" className={`form-control ${errors.email ? 'is-invalid' : ''}`} value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} />
                {errors.email && <div className="invalid-feedback">{errors.email}</div>}
              </div>
              <div className="mb-3">
                <label className="form-label">Пароль</label>
                <input type="password" className={`form-control ${errors.password ? 'is-invalid' : ''}`} value={formData.password} onChange={(e) => setFormData({...formData, password: e.target.value})} />
                {errors.password && <div className="invalid-feedback">{errors.password}</div>}
              </div>
              <div className="d-grid gap-2">
                <button type="submit" className="btn btn-primary" disabled={isLoading}>
                  {isLoading ? <span className="spinner-border spinner-border-sm"></span> : 'Увійти'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

function GameDetailsModal({ game, show, onClose, user, onPurchase, keysDB, saveKeysDB, usersDB, saveUsersDB }) {
  const [purchaseStatus, setPurchaseStatus] = React.useState(null);
  const [isProcessing, setIsProcessing] = React.useState(false);

  React.useEffect(() => {
    setPurchaseStatus(null);
  }, [game]);

  if (!show || !game) return null;

  const finalPrice = Math.round(game.price * (1 - game.discount / 100));
  const availableKeys = keysDB[game.id.toString()] || [];

  const handlePurchase = async () => {
    if (!user) { alert('Будь ласка, увійдіть в акаунт для покупки'); return; }
    if (user.balance < finalPrice) { setPurchaseStatus('insufficient'); return; }
    if (availableKeys.length === 0) { setPurchaseStatus('no_keys'); return; }

    setIsProcessing(true);
    await new Promise(resolve => setTimeout(resolve, 1000));

    const purchasedKeyObject = availableKeys.shift();
    const updatedKeys = { ...keysDB, [game.id.toString()]: availableKeys };
    saveKeysDB(updatedKeys);

    const updatedUser = {
      ...user,
      balance: user.balance - finalPrice,
      totalSpent: user.totalSpent + finalPrice,
      purchasedGames: [...user.purchasedGames, {
        gameId: game.id,
        gameTitle: game.title,
        key: purchasedKeyObject.key,
        keyImage: purchasedKeyObject.image,
        price: finalPrice,
        purchaseDate: new Date().toISOString()
      }]
    };

    const updatedUsers = { ...usersDB, [user.email]: updatedUser };
    saveUsersDB(updatedUsers);

    setPurchaseStatus('success');
    onPurchase(updatedUser);
    setIsProcessing(false);
  };

  return (
    <div className="modal show d-block" style={{backgroundColor: 'rgba(0,0,0,0.5)'}}>
      <div className="modal-dialog modal-lg modal-dialog-centered">
        <div className="modal-content">
          <div className="modal-header"><h5 className="modal-title">{game.title}</h5><button type="button" className="btn-close" onClick={onClose}></button></div>
          <div className="modal-body">
            {purchaseStatus === 'success' && <div className="purchase-success"><h6 className="text-success"><i className="fas fa-check-circle me-2"></i>Покупка успішна!</h6><p>Ваша закладка вже додана.</p></div>}
            {purchaseStatus === 'insufficient' && <div className="insufficient-funds"><h6 className="text-danger"><i className="fas fa-exclamation-triangle me-2"></i>Недостатньо коштів</h6></div>}
            {purchaseStatus === 'no_keys' && <div className="insufficient-funds"><h6 className="text-danger"><i className="fas fa-exclamation-triangle me-2"></i>Закладок більше нема 😞</h6></div>}
            <div className="row">
              <div className="col-md-6"><img src={game.image} alt={game.title} className="img-fluid rounded" /></div>
              <div className="col-md-6">
                <p><strong>Платформа:</strong> {game.platform}</p>
                <p><strong>Залишилось:</strong> <span className="badge bg-info">{availableKeys.length}</span></p>
                <div className="mb-3">
                  {game.discount > 0 && (<><span className="badge bg-danger me-2">-{game.discount}%</span><span className="text-decoration-line-through text-muted me-2">{game.price} ₴</span></>)}
                  <h4 className="text-primary d-inline-block">{finalPrice} ₴</h4>
                </div>
                <p>{game.description}</p>
              </div>
            </div>
          </div>
          <div className="modal-footer">
            {user && <div className="me-auto"><small className="text-muted">Ваш баланс: </small><span className="balance-display">{user.balance} ₴</span></div>}
            <button className="btn btn-primary" disabled={availableKeys.length === 0 || !user || isProcessing} onClick={handlePurchase}>
              {isProcessing ? <span className="spinner-border spinner-border-sm me-2"></span> : <i className="fas fa-shopping-cart me-2"></i>}
            Халява
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ProfileModal({ user, show, onClose }) {
  if (!show || !user) return null;
  return (
    <div className="modal show d-block" style={{backgroundColor: 'rgba(0,0,0,0.5)'}}>
      <div className="modal-dialog modal-lg modal-dialog-centered">
        <div className="modal-content">
          <div className="modal-header"><h5 className="modal-title">Особистий кабінет</h5><button type="button" className="btn-close" onClick={onClose}></button></div>
          <div className="modal-body">
            <div className="row mb-4">
              <div className="col-md-6">
                <h6>Інформація про акаунт</h6>
                <p><strong>Ім'я:</strong> {user.name}</p>
                <p><strong>Email:</strong> {user.email}</p>
                <p><strong>Дата реєстрації:</strong> {new Date(user.registrationDate).toLocaleDateString('uk-UA')}</p>
              </div>
              <div className="col-md-6">
                <h6>Статистика</h6>
                <p><strong>Поточний баланс:</strong> <span className="balance-display">{user.balance} ₴</span></p>
                <p><strong>Всього витрачено:</strong> {user.totalSpent} ₴</p>
                <p><strong>Куплено пріколов:</strong> {user.purchasedGames.length}</p>
              </div>
            </div>
            <h6>Куплені шишулі</h6>
            {user.purchasedGames.length === 0 ? <p className="text-muted">Ви ще не купували жодного грамма.</p> : (
              <div className="table-responsive">
                <table className="table table-striped align-middle">
                  <thead><tr><th>Прікол</th><th>Місце закладки</th><th>Ціна</th><th>Дата</th></tr></thead>
                  <tbody>
                  {user.purchasedGames.map((p, i) => (
                    <tr key={i}>
                      <td>{p.gameTitle}</td>
                      <td>
                        <div className="d-flex align-items-center">
                          <img src={p.keyImage} alt="Зображення ключа" className="me-3" style={{width: '120px', borderRadius: '4px'}} />
                          <code className="bg-light p-1 rounded">{p.key}</code>
                        </div>
                      </td>
                      <td>{p.price} ₴</td>
                      <td>{new Date(p.purchaseDate).toLocaleDateString('uk-UA')}</td>
                    </tr>
                  ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
