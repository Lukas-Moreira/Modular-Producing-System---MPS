import time
import pyodbc
from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt

# ========================================
# CONFIGURAÇÕES DE SEGURANÇA
# ========================================

SECRET_KEY = "sua-chave-secreta-super-segura-mude-isso-em-producao-123456"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 horas

security = HTTPBearer()

# ========================================
# MODELS
# ========================================

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    access_token: str = None
    token_type: str = "bearer"
    user: dict = None

# ========================================
# FUNÇÕES DE AUTENTICAÇÃO
# ========================================

def create_access_token(data: dict):
    """Cria token JWT"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verifica se o token é válido"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

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
# BANCO DE DADOS
# ========================================

def get_db_connection():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost\\SQLEXPRESS;'
        'DATABASE=db_mps;'
        'Trusted_Connection=yes;'
    )
    return conn

def set_mes_instance(mes):
    global mes_instance
    mes_instance = mes

# ========================================
# ROTA DE LOGIN (PÚBLICA)
# ========================================

@app.post("/api/login", response_model=LoginResponse)
def login(credentials: LoginRequest):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT username 
        FROM users 
        WHERE username = ? AND password = ?
        """
        
        cursor.execute(query, (credentials.username, credentials.password))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            # Cria o token JWT
            access_token = create_access_token(data={"sub": credentials.username})
            
            return LoginResponse(
                success=True,
                message="Login realizado com sucesso",
                access_token=access_token,
                token_type="bearer",
                user={
                    "username": credentials.username,
                    "role": "admin"
                }
            )
        else:
            raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Erro no login: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar login: {str(e)}")

# ========================================
# ROTAS PÚBLICAS (SEM AUTENTICAÇÃO)
# ========================================

@app.get("/api/machine-status")
def get_machine_status():
    active_order = None
    
    if mes_instance:
        active_order_data = mes_instance.get_active_order()
        
        if active_order_data:
            remaining = active_order_data['quantity_requested'] - active_order_data['quantity_processed']
            active_order = {
                "order_name": active_order_data['order_name'],
                "color_requested": active_order_data['color_requested'],
                "quantity_requested": active_order_data['quantity_requested'],
                "quantity_processed": active_order_data['quantity_processed'],
                "quantity_remaining": remaining
            }
        
        return {
            "status": mes_instance.state_machine,
            "conveyor_available": mes_instance.is_conveyor_available,
            "active_order": active_order,
            "timestamp": time.time()
        }
    else:
        return {
            "status": "unknown",
            "conveyor_available": False,
            "active_order": None,
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
        WHERE CAST(created_at AS DATE) = CAST(GETDATE() AS DATE)
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
        WHERE CAST(created_at AS DATE) = CAST(GETDATE() AS DATE)
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

@app.get("/api/recent-pieces")
def get_recent_pieces(
    page: int = Query(1, ge=1),
    page_size: int = Query(8, ge=1, le=50),
    date_filter: str = Query(None)
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        offset = (page - 1) * page_size
        
        date_condition = ""
        if date_filter:
            date_condition = f"WHERE CAST(p.created_at AS DATE) = '{date_filter}'"
        else:
            date_condition = "WHERE CAST(p.created_at AS DATE) = CAST(GETDATE() AS DATE)"
        
        count_query = f"""
        SELECT COUNT(*) AS total
        FROM pieces p
        {date_condition}
        """
        
        cursor.execute(count_query)
        total_count = cursor.fetchone().total
        
        query = f"""
        SELECT 
            p.id,
            p.piece_color,
            p.result,
            p.order_id,
            p.created_at,
            po.order_name
        FROM pieces p
        LEFT JOIN production_orders po ON p.order_id = po.id
        {date_condition}
        ORDER BY p.created_at DESC
        OFFSET {offset} ROWS
        FETCH NEXT {page_size} ROWS ONLY
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        conn.close()
        
        pieces = []
        for row in rows:
            pieces.append({
                "id": row.id,
                "piece_color": row.piece_color,
                "result": row.result,
                "order_id": row.order_id,
                "order_name": row.order_name if row.order_name else "Sem ordem",
                "created_at": row.created_at.isoformat() if row.created_at else None
            })
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            "pieces": pieces,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "timestamp": time.time()
        }
        
    except Exception as e:
        print(f"Erro ao buscar peças: {e}")
        import traceback
        traceback.print_exc()
        return {
            "pieces": [],
            "total_count": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
            "timestamp": time.time()
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


@app.post("/api/create-order")
def create_order(order: dict, username: str = Depends(verify_token)):
    """Criar ordem - REQUER AUTENTICAÇÃO"""
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
        
        print(f"Nova ordem criada por {username}: {order}")
        return {
            "success": True,
            "message": "Ordem criada com sucesso",
            "order": order,
            "created_by": username
        }
        
    except Exception as e:
        print(f"Erro ao criar ordem: {e}")
        return {
            "success": False,
            "message": f"Erro ao criar ordem: {str(e)}",
            "order": order
        }