import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './Dashboard.css';

interface ActiveOrder {
  order_name: string;
  color_requested: string;
  quantity_requested: number;
  quantity_processed: number;
  quantity_remaining: number;
}

interface MachineStatus {
  status: string;
  conveyor_available: boolean;
  active_order: ActiveOrder | null;
  timestamp: number;
}

interface ProductionStats {
  total_pieces: number;
  rejected_pieces: number;
  approved_pieces: number;
  timestamp: number;
}

interface HourlyDataPoint {
  hour: string;
  total: number;
  rejected: number;
  approved: number;
}

interface Order {
  id: number;
  order_name: string;
  color_requested: string;
  quantity_requested: number;
  quantity_processed: number;
  created_at: string;
  finished_at: string | null;
}

interface Piece {
  id: number;
  piece_color: string;
  result: boolean;
  order_id: number | null;
  order_name: string;
  created_at: string;
}

interface PiecesResponse {
  pieces: Piece[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  timestamp: number;
}

const Dashboard: React.FC = () => {
  const [machineStatus, setMachineStatus] = useState<MachineStatus | null>(null);
  const [productionStats, setProductionStats] = useState<ProductionStats | null>(null);
  const [hourlyData, setHourlyData] = useState<HourlyDataPoint[]>([]);
  const [recentOrders, setRecentOrders] = useState<Order[]>([]);
  const [recentPieces, setRecentPieces] = useState<Piece[]>([]);
  const [piecesPage, setPiecesPage] = useState(1);
  const [piecesTotalPages, setPiecesTotalPages] = useState(1);
  const [dateFilter, setDateFilter] = useState<string>('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statusRes, statsRes, hourlyRes, ordersRes] = await Promise.all([
          axios.get<MachineStatus>('http://localhost:8000/api/machine-status'),
          axios.get<ProductionStats>('http://localhost:8000/api/production-stats'),
          axios.get<{ hourly_data: HourlyDataPoint[] }>('http://localhost:8000/api/hourly-production'),
          axios.get<{ orders: Order[] }>('http://localhost:8000/api/recent-orders')
        ]);

        setMachineStatus(statusRes.data);
        setProductionStats(statsRes.data);
        setHourlyData(hourlyRes.data.hourly_data);
        setRecentOrders(ordersRes.data.orders);
      } catch (error) {
        console.error('Erro ao buscar dados:', error);
      }
    };  

    fetchData();
    const interval = setInterval(fetchData, 2000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    fetchPieces();
    const interval = setInterval(fetchPieces, 2000);
    return () => clearInterval(interval);
  }, [piecesPage, dateFilter]);

  const fetchPieces = async () => {
    try {
      const params: any = {
        page: piecesPage,
        page_size: 8
      };

      if (dateFilter) {
        params.date_filter = dateFilter;
      }

      const response = await axios.get<PiecesResponse>('http://localhost:8000/api/recent-pieces', { params });
      setRecentPieces(response.data.pieces);
      setPiecesTotalPages(response.data.total_pages);
    } catch (error) {
      console.error('Erro ao buscar peças:', error);
    }
  };

  const getStatusBadge = (order: Order) => {
    if (order.finished_at) return <span className="status-badge completed">Concluída</span>;
    if (order.quantity_processed > 0) return <span className="status-badge in-progress">Em Progresso</span>;
    return <span className="status-badge pending">Pendente</span>;
  };

  const getStatusText = (status: string) => {
    const statusMap: { [key: string]: string } = {
      'running': 'EM OPERAÇÃO',
      'idle': 'AGUARDANDO',
      'stopped': 'PARADA',
      'error': 'ERRO',
      'cycle': 'CICLO',
      'emergency': 'EMERGÊNCIA'
    };
    return statusMap[status] || 'DESCONHECIDO';
  };

  const getProgressPercentage = (order: ActiveOrder) => {
    return (order.quantity_processed / order.quantity_requested) * 100;
  };

  const handlePreviousPage = () => {
    if (piecesPage > 1) {
      setPiecesPage(piecesPage - 1);
    }
  };

  const handleNextPage = () => {
    if (piecesPage < piecesTotalPages) {
      setPiecesPage(piecesPage + 1);
    }
  };

  const handleDateFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDateFilter(e.target.value);
    setPiecesPage(1);
  };

  const clearDateFilter = () => {
    setDateFilter('');
    setPiecesPage(1);
  };

  return (
    <div className="dashboard-page">
      <div className="production-cards">
        <div className="stat-card total">
          <img src="/total.svg" alt="Total" className="stat-icon-img" />
          <div className="stat-content">
            <h3>{productionStats?.total_pieces || 0}</h3>
            <p>Total de Peças</p>
          </div>
        </div>

        <div className="stat-card approved">
          <img src="/approved.svg" alt="Aprovadas" className="stat-icon-img" />
          <div className="stat-content">
            <h3>{productionStats?.approved_pieces || 0}</h3>
            <p>Peças Aprovadas</p>
          </div>
        </div>

        <div className="stat-card rejected">
          <img src="/reproved.svg" alt="Rejeitadas" className="stat-icon-img" />
          <div className="stat-content">
            <h3>{productionStats?.rejected_pieces || 0}</h3>
            <p>Peças Rejeitadas</p>
          </div>
        </div>
      </div>

      <div className="main-grid">
        <div className="card status-card">
          <h2>Status da Máquina</h2>
          {machineStatus && (
            <>
              <div className={`machine-status ${machineStatus.status}`}>
                <div className="status-indicator"></div>
                <span>{getStatusText(machineStatus.status)}</span>
              </div>
              
              <div className="conveyor-status">
                <div className={`conveyor-indicator ${machineStatus.conveyor_available ? 'available' : 'busy'}`}></div>
                <span>Esteira: {machineStatus.conveyor_available ? 'Disponível' : 'Ocupada'}</span>
              </div>

              {machineStatus.active_order ? (
                <div className="active-order-info">
                  <h3>Ordem Atual</h3>
                  <div className="order-details">
                    <div className="order-header">
                      <span className="order-title">{machineStatus.active_order.order_name}</span>
                      <span className={`order-color-badge ${machineStatus.active_order.color_requested}`}>
                        {machineStatus.active_order.color_requested}
                      </span>
                    </div>
                    
                    <div className="order-stats">
                      <div className="stat-item">
                        <span className="stat-label">Processadas</span>
                        <span className="stat-value">{machineStatus.active_order.quantity_processed}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Restantes</span>
                        <span className="stat-value">{machineStatus.active_order.quantity_remaining}</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-label">Total</span>
                        <span className="stat-value">{machineStatus.active_order.quantity_requested}</span>
                      </div>
                    </div>

                    <div className="order-progress">
                      <div className="progress-bar-container">
                        <div 
                          className="progress-bar-fill" 
                          style={{ width: `${getProgressPercentage(machineStatus.active_order)}%` }}
                        ></div>
                      </div>
                      <span className="progress-text">
                        {getProgressPercentage(machineStatus.active_order).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="no-active-order">
                  <p>Nenhuma ordem ativa</p>
                </div>
              )}
            </>
          )}
        </div>

        <div className="card chart-card">
          <h2>Produção por Hora</h2>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={hourlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
              <XAxis dataKey="hour" stroke="#666" />
              <YAxis stroke="#666" />
              <Tooltip />
              <Legend />
              <Bar dataKey="approved" fill="#2D5F3F" name="Aprovadas" radius={[8, 8, 0, 0]} />
              <Bar dataKey="rejected" fill="#D32F2F" name="Rejeitadas" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="tables-grid">
        <div className="card orders-table-card">
          <h2>Ordens Recentes</h2>
          <div className="table-container">
            <table className="orders-table">
              <thead>
                <tr>
                  <th>Ordem</th>
                  <th>Cor</th>
                  <th>Solicitado</th>
                  <th>Processado</th>
                  <th>Criado em</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {recentOrders.map((order) => (
                  <tr key={order.id}>
                    <td className="order-name">{order.order_name}</td>
                    <td>
                      <span className={`color-badge ${order.color_requested}`}>
                        {order.color_requested}
                      </span>
                    </td>
                    <td>{order.quantity_requested}</td>
                    <td>{order.quantity_processed}</td>
                    <td>{new Date(order.created_at).toLocaleString('pt-BR')}</td>
                    <td>{getStatusBadge(order)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card pieces-table-card">
          <div className="pieces-header">
            <h2>Últimas Peças</h2>
            <div className="pieces-filter">
              <input
                type="date"
                value={dateFilter}
                onChange={handleDateFilterChange}
                className="date-filter-input"
              />
              {dateFilter && (
                <button onClick={clearDateFilter} className="clear-filter-btn">
                  Limpar
                </button>
              )}
            </div>
          </div>
          <div className="table-container">
            <table className="pieces-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Cor</th>
                  <th>Resultado</th>
                  <th>Ordem</th>
                  <th>Processado em</th>
                </tr>
              </thead>
              <tbody>
                {recentPieces.map((piece) => (
                  <tr key={piece.id}>
                    <td className="piece-id">#{piece.id}</td>
                    <td>
                      <span className={`color-badge ${piece.piece_color}`}>
                        {piece.piece_color}
                      </span>
                    </td>
                    <td>
                      <span className={`result-badge ${piece.result === true ? 'approved' : 'rejected'}`}>
                        {piece.result === true ? 'Aprovada' : 'Rejeitada'}
                      </span>
                    </td>
                    <td className="piece-order">{piece.order_name}</td>
                    <td>{new Date(piece.created_at).toLocaleString('pt-BR')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <button 
              onClick={handlePreviousPage} 
              disabled={piecesPage === 1}
              className="pagination-btn"
            >
              Anterior
            </button>
            <span className="pagination-info">
              Página {piecesPage} de {piecesTotalPages}
            </span>
            <button 
              onClick={handleNextPage} 
              disabled={piecesPage === piecesTotalPages}
              className="pagination-btn"
            >
              Próxima
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;