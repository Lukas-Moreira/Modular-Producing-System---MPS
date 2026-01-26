import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';
import LoginModal from '../components/LoginModal';
import './Orders.css';

const API_URL = "http://192.168.0.77:8000/";

interface Order {
  id: number;
  order_name: string;
  color_requested: string;
  quantity_requested: number;
  quantity_processed: number;
  created_at: string;
  finished_at: string | null;
}

interface OrderForm {
  orderName: string;
  color: string;
  quantity: number;
}

const Orders: React.FC = () => {
  const [formData, setFormData] = useState<OrderForm>({
    orderName: '',
    color: 'prata',
    quantity: 1
  });
  const [orders, setOrders] = useState<Order[]>([]);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);

  useEffect(() => {
    const auth = localStorage.getItem('isAuthenticated');
    const token = localStorage.getItem('access_token');
    setIsAuthenticated(auth === 'true' && token !== null);
    
    fetchOrders();
    const interval = setInterval(fetchOrders, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchOrders = async () => {
    try {
      const response = await axios.get<{ orders: Order[] }>(`${API_URL}api/recent-orders`);
      setOrders(response.data.orders);
    } catch (error) {
      console.error('Erro ao buscar ordens:', error);
    }
  };

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
    setShowLoginModal(false);
    toast.success('Login realizado com sucesso!');
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('user');
    setIsAuthenticated(false);
    toast.info('Logout realizado com sucesso');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isAuthenticated) {
      setShowLoginModal(true);
      return;
    }

    if (!formData.orderName.trim()) {
      toast.error('Por favor, preencha o nome da ordem!');
      return;
    }

    if (formData.quantity < 1) {
      toast.error('A quantidade deve ser maior que 0!');
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      
      await axios.post(`${API_URL}api/create-order`, formData, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      toast.success(`Ordem "${formData.orderName}" criada com sucesso!`);
      
      setFormData({
        orderName: '',
        color: 'prata',
        quantity: 1
      });

      fetchOrders();
    } catch (error: any) {
      if (error.response?.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('isAuthenticated');
        localStorage.removeItem('user');
        setIsAuthenticated(false);
        setShowLoginModal(true);
        toast.error('Sessão expirada! Faça login novamente.');
      } else {
        toast.error('Erro ao criar ordem. Tente novamente.');
      }
      console.error('Erro:', error);
    }
  };

  const getStatusBadge = (order: Order) => {
    if (order.finished_at) return <span className="status-badge completed">Concluída</span>;
    if (order.quantity_processed > 0) return <span className="status-badge in-progress">Em Progresso</span>;
    return <span className="status-badge pending">Pendente</span>;
  };

  const getProgress = (order: Order) => {
    return (order.quantity_processed / order.quantity_requested) * 100;
  };

  return (
    <div className="orders-page">
      <LoginModal
        isOpen={showLoginModal}
        onClose={() => setShowLoginModal(false)}
        onSuccess={handleLoginSuccess}
      />

      <div className="orders-grid">
        <div className="card form-card">
          <div className="form-header">
            <h2>Nova Ordem de Produção</h2>
            {isAuthenticated && (
              <button className="logout-btn" onClick={handleLogout}>
                Sair
              </button>
            )}
          </div>
          
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Nome da Ordem</label>
              <input
                type="text"
                placeholder="Ex: ORDEM_001"
                value={formData.orderName}
                onChange={(e) => setFormData({ ...formData, orderName: e.target.value })}
                required
              />
            </div>

            <div className="form-group">
              <label>Cor da Peça</label>
              <div className="color-options">
                <div
                  className={`color-option ${formData.color === 'prata' ? 'selected' : ''}`}
                  onClick={() => setFormData({ ...formData, color: 'prata' })}
                >
                  <div className="color-circle prata-bg"></div>
                  <span>Prata</span>
                </div>

                <div
                  className={`color-option ${formData.color === 'preto' ? 'selected' : ''}`}
                  onClick={() => setFormData({ ...formData, color: 'preto' })}
                >
                  <div className="color-circle preto-bg"></div>
                  <span>Preto</span>
                </div>

                <div
                  className={`color-option ${formData.color === 'rosa' ? 'selected' : ''}`}
                  onClick={() => setFormData({ ...formData, color: 'rosa' })}
                >
                  <div className="color-circle rosa-bg"></div>
                  <span>Rosa</span>
                </div>
              </div>
            </div>

            <div className="form-group">
              <label>Quantidade</label>
              <input
                type="number"
                min="1"
                value={formData.quantity}
                onChange={(e) => setFormData({ ...formData, quantity: parseInt(e.target.value) || 1 })}
                required
              />
            </div>

            <button type="submit" className="submit-btn">
              {isAuthenticated ? 'Criar Ordem' : '🔒  Criar ordem'}
            </button>
          </form>
        </div>

        <div className="card list-card">
          <h2>Últimas Ordens</h2>
          <div className="orders-list">
            {orders.map((order) => (
              <div key={order.id} className="order-item">
                <div className="order-header">
                  <span className="order-name">{order.order_name}</span>
                  {getStatusBadge(order)}
                </div>
                <div className="order-info">
                  <span className={`color-badge ${order.color_requested}`}>
                    {order.color_requested}
                  </span>
                  <span className="order-quantity">
                    {order.quantity_processed} / {order.quantity_requested} peças
                  </span>
                </div>
                <div className="progress-bar">
                  <div 
                    className="progress-fill" 
                    style={{ width: `${getProgress(order)}%` }}
                  ></div>
                </div>
                <div className="order-date">
                  Criado em: {new Date(order.created_at).toLocaleString('pt-BR')}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Orders;