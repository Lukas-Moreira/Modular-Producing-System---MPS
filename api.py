import time
import pyodbc
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ========================================
# CONFIGURAÇÃO DO FASTAPI
# ========================================

app = FastAPI(
    title="MPS Festo API",
    description="API para monitoramento e controle do sistema MPS Festo",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ========================================

def get_db_connection():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost\\SQLEXPRESS;'
        'DATABASE=db_mps;'
        'Trusted_Connection=yes;'
    )
    return conn

# ========================================
# DADOS MOCKADOS (APENAS SENSORES)
# ========================================

mock_machine_status = {
    "status": "running",
    "sensors": {
        "sensor_peca_suporte": 1,
        "sensor_braco_deixa": 0,
        "sensor_braco_home": 1,
        "sensor_braco_rejeito": 0,
        "sensor_garra_avancada": 0,
        "sensor_garra_recuada": 1,
        "sensor_peca_garra": 0
    }
}

# ========================================
# ROTAS DA API
# ========================================

@app.get("/api/machine-status")
def get_machine_status():
    return {
        **mock_machine_status,
        "timestamp": time.time()
    }

@app.get("/api/production-stats")
def get_production_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT 
            COUNT(id) AS total_pieces,
            SUM(CASE WHEN result = 1 THEN 1 ELSE 0 END) AS approved_pieces,
            SUM(CASE WHEN result = 0 THEN 1 ELSE 0 END) AS rejected_pieces
        FROM pieces
        WHERE CAST(created_at AS DATE) = '2026-01-13'
        """
        
        cursor.execute(query)
        row = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_pieces": row.total_pieces or 0,
            "approved_pieces": row.approved_pieces or 0,
            "rejected_pieces": row.rejected_pieces or 0,
            "timestamp": time.time()
        }
        
    except Exception as e:
        print(f"Erro ao buscar estatísticas: {e}")
        return {
            "total_pieces": 0,
            "approved_pieces": 0,
            "rejected_pieces": 0,
            "timestamp": time.time()
        }

@app.get("/api/hourly-production")
def get_hourly_production():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT 
            FORMAT(created_at, 'HH:00') AS hour,
            COUNT(id) AS total,
            SUM(CASE WHEN result = 1 THEN 1 ELSE 0 END) AS approved,
            SUM(CASE WHEN result = 0 THEN 1 ELSE 0 END) AS rejected
        FROM pieces
        WHERE CAST(created_at AS DATE) = '2026-01-13'
        GROUP BY FORMAT(created_at, 'HH:00')
        ORDER BY FORMAT(created_at, 'HH:00')
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        
        conn.close()
        
        hourly_data = []
        for row in rows:
            hourly_data.append({
                "hour": row.hour,
                "total": row.total,
                "approved": row.approved,
                "rejected": row.rejected
            })
        
        # print(f"Hourly data: {hourly_data}")
        
        return {
            "hourly_data": hourly_data,
            "timestamp": time.time()
        }
        
    except Exception as e:
        print(f"Erro ao buscar produção por hora: {e}")
        import traceback
        traceback.print_exc()
        return {
            "hourly_data": [],
            "timestamp": time.time()
        }
    
@app.post("/api/create-order")
def create_order(order: dict):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        INSERT INTO production_orders (order_name, quantity_requested, quantity_processed, color_requested)
        VALUES (?, ?, 0, ?)
        """
        
        cursor.execute(query, order['orderName'], order['quantity'], order['color'])
        conn.commit()
        conn.close()
        
        print(f"Nova ordem criada: {order}")
        return {
            "success": True,
            "message": "Ordem criada com sucesso",
            "order": order
        }
        
    except Exception as e:
        print(f"Erro ao criar ordem: {e}")
        return {
            "success": False,
            "message": f"Erro ao criar ordem: {str(e)}",
            "order": order
        }
    
@app.get("/api/recent-orders")
def get_recent_orders():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT TOP 10
            id,
            order_name,
            color_requested,
            quantity_requested,
            quantity_processed,
            created_at,
            finished_at
        FROM production_orders
        ORDER BY created_at DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        conn.close()
        
        orders = []
        for row in rows:
            orders.append({
                "id": row.id,
                "order_name": row.order_name,
                "color_requested": row.color_requested,
                "quantity_requested": row.quantity_requested,
                "quantity_processed": row.quantity_processed,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "finished_at": row.finished_at.isoformat() if row.finished_at else None
            })
        
        return {
            "orders": orders,
            "timestamp": time.time()
        }
        
    except Exception as e:
        print(f"Erro ao buscar ordens: {e}")
        import traceback
        traceback.print_exc()
        return {
            "orders": [],
            "timestamp": time.time()
        }