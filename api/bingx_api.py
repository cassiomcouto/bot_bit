#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente API para BingX Perpetual Futures
"""

import logging
import time
import hmac
import hashlib
import urllib.parse
import requests
from datetime import datetime
from typing import Dict, List
from models.data_classes import BingXOrder, BingXPosition

logger = logging.getLogger(__name__)

class BingXFuturesAPI:
    """Cliente API para BingX Perpetual Futures"""
    
    def __init__(self, api_key: str, secret_key: str, testnet: bool = False):
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet
        
        self.base_url = "https://open-api-vst.bingx.com" if testnet else "https://open-api.bingx.com"
            
        self.session = requests.Session()
        self.session.headers.update({
            'X-BX-APIKEY': self.api_key,
            'User-Agent': 'BingX-Python-Client/1.0',
            'Accept': 'application/json',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache'
        })
        
        # Configurações de timeout e retry
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _generate_signature(self, params_str: str) -> str:
        """Gera assinatura HMAC SHA256"""
        return hmac.new(
            self.secret_key.encode('utf-8'), 
            params_str.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()

    def _send_signed_request(self, endpoint: str, params: Dict = None, method: str = 'GET') -> Dict:
        """Envia requisição assinada para BingX - Versão com melhor tratamento de conexão"""
        try:
            if params is None:
                params = {}
            
            params['timestamp'] = int(time.time() * 1000)
            
            # Remove Content-Type para POST, pois conflita com parâmetros na URL
            headers = {
                'X-BX-APIKEY': self.api_key,
                'User-Agent': 'BingX-Python-Client/1.0',
                'Accept': 'application/json'
            }
            
            if method.upper() == 'GET':
                # GET: NÃO ordena parâmetros (igual ao POST que funciona)
                query_string = urllib.parse.urlencode(params)
                signature = self._generate_signature(query_string)
                params['signature'] = signature
                
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, params=params, headers=headers, timeout=30)
                
            elif method.upper() == 'POST':
                # POST: NÃO ordena os parâmetros para assinatura
                query_string = urllib.parse.urlencode(params)
                signature = self._generate_signature(query_string)
                params['signature'] = signature
                
                # Para POST, coloca todos os parâmetros na URL
                url = f"{self.base_url}{endpoint}?{urllib.parse.urlencode(params)}"
                response = requests.post(url, headers=headers, timeout=30)
                
            elif method.upper() == 'DELETE':
                # DELETE: NÃO ordena parâmetros (consistente com POST)
                query_string = urllib.parse.urlencode(params)
                signature = self._generate_signature(query_string)
                params['signature'] = signature
                
                url = f"{self.base_url}{endpoint}"
                response = requests.delete(url, params=params, headers=headers, timeout=30)
                
            else:
                raise ValueError(f"Método não suportado: {method}")
            
            response.raise_for_status()
            
            # Verifica se a resposta é JSON válida
            try:
                data = response.json()
            except ValueError as e:
                logger.error(f"Resposta não é JSON válida: {response.text[:200]}")
                raise Exception(f"Resposta inválida da BingX: {e}")
            
            if data.get('code') != 0:
                error_msg = data.get('msg', 'Unknown error')
                logger.error(f"Erro da API BingX (code: {data.get('code')}): {error_msg}")
                raise Exception(f"BingX API Error: {error_msg}")
            
            return data.get('data', data)
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Erro de conexão com BingX: {e}")
            # Aguarda um pouco antes de tentar novamente
            time.sleep(2)
            raise Exception(f"Falha na conexão com BingX. Verifique sua conexão de internet.")
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout na requisição para BingX: {e}")
            raise Exception(f"Timeout na requisição. BingX pode estar sobrecarregada.")
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erro HTTP: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Resposta HTTP: {e.response.status_code} - {e.response.text[:200]}")
            raise Exception(f"Erro HTTP da BingX: {e}")
            
        except Exception as e:
            logger.error(f"Erro geral na API BingX: {e}")
            raise

    def get_account_info(self) -> Dict:
        """Obtém informações da conta com retry automático"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"Tentativa {attempt + 1} de obter info da conta...")
                    time.sleep(2 ** attempt)  # Backoff exponencial
                
                return self._send_signed_request('/openApi/swap/v2/user/balance')
                
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Falha após {max_retries} tentativas: {e}")
                    raise
                logger.warning(f"Tentativa {attempt + 1} falhou: {e}")
        
        return {}

    def health_check(self) -> bool:
        """Verifica se a conexão com BingX está funcionando"""
        try:
            # Testa endpoint público primeiro
            url = f"{self.base_url}/openApi/swap/v2/quote/price"
            params = {"symbol": "BTC-USDT"}
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                logger.error(f"Health check falhou: HTTP {response.status_code}")
                return False
            
            data = response.json()
            if data.get('code') != 0:
                logger.error(f"Health check falhou: {data.get('msg', 'Unknown error')}")
                return False
            
            # Testa endpoint autenticado
            account_info = self.get_account_info()
            if not account_info:
                return False
                
            logger.info("Health check BingX: OK")
            return True
            
        except Exception as e:
            logger.error(f"Health check falhou: {e}")
            return False

    def get_positions(self) -> List[BingXPosition]:
        """Obtém posições abertas"""
        try:
            data = self._send_signed_request('/openApi/swap/v2/user/positions')
            positions = []
            
            positions_data = data if isinstance(data, list) else data.get('data', [])
            
            for pos_data in positions_data:
                position_amt = float(pos_data.get('positionAmt', 0))
                if position_amt != 0:
                    # Mapeia campos da BingX
                    entry_price = 0.0
                    for field in ['entryPrice', 'avgPrice', 'openPrice']:
                        if field in pos_data:
                            entry_price = float(pos_data[field])
                            break
                    
                    mark_price = entry_price
                    for field in ['markPrice', 'lastPrice']:
                        if field in pos_data:
                            mark_price = float(pos_data[field])
                            break
                    
                    position = BingXPosition(
                        symbol=pos_data.get('symbol', ''),
                        positionSide=pos_data.get('positionSide', 'LONG'),
                        size=abs(position_amt),
                        entryPrice=entry_price,
                        markPrice=mark_price,
                        unrealizedPnl=float(pos_data.get('unrealizedProfit', 0)),
                        marginUsed=float(pos_data.get('positionInitialMargin', 0)),
                        leverage=int(pos_data.get('leverage', 1))
                    )
                    positions.append(position)
            
            return positions
            
        except Exception as e:
            logger.error(f"Erro ao buscar posições: {e}")
            return []

    def get_open_orders(self, symbol: str = None) -> List[BingXOrder]:
        """Obtém ordens abertas"""
        try:
            params = {}
            if symbol:
                params['symbol'] = symbol
                
            data = self._send_signed_request('/openApi/swap/v2/trade/openOrders', params)
            orders = []
            
            # Trata diferentes formatos de resposta
            if isinstance(data, list):
                orders_data = data
            elif isinstance(data, dict):
                orders_data = data.get('data', []) if data else []
            else:
                orders_data = []
            
            for order_data in orders_data:
                if isinstance(order_data, dict):
                    order = BingXOrder(
                        orderId=order_data.get('orderId', ''),
                        symbol=order_data.get('symbol', ''),
                        side=order_data.get('side', ''),
                        positionSide=order_data.get('positionSide', ''),
                        type=order_data.get('type', ''),
                        quantity=float(order_data.get('origQty', 0)),
                        price=float(order_data.get('price', 0))
                    )
                    orders.append(order)
            
            return orders
            
        except Exception as e:
            logger.error(f"Erro ao buscar ordens: {e}")
            return []

    def place_order(self, symbol: str, side: str, position_side: str, 
                   quantity: float, order_type: str = "MARKET", 
                   price: float = None, reduce_only: bool = False) -> Dict:
        """Coloca uma ordem - Versão corrigida para modo Hedge"""
        try:
            # Formata quantidade com precisão adequada
            if "BTC" in symbol:
                quantity_str = f"{quantity:.3f}"
            elif "ETH" in symbol:
                quantity_str = f"{quantity:.4f}"
            else:
                quantity_str = f"{quantity:.4f}"
            
            params = {
                'symbol': symbol,
                'side': side.upper(),
                'positionSide': position_side.upper(),
                'type': order_type.upper(),
                'quantity': quantity_str
            }
            
            if price and order_type.upper() == 'LIMIT':
                params['price'] = str(price)
                params['timeInForce'] = 'GTC'
            
            # CORREÇÃO: No modo Hedge, NÃO incluir reduceOnly
            # Para fechar posição no Hedge, use a direção oposta sem reduceOnly
            # if reduce_only:
            #     params['reduceOnly'] = 'true'  # REMOVIDO para modo Hedge
            
            logger.info(f"Colocando ordem: {side} {quantity_str} {symbol}")
            logger.info(f"Parâmetros: {params}")
            
            result = self._send_signed_request('/openApi/swap/v2/trade/order', params, 'POST')
            
            # Validação automática
            try:
                order_id = result.get('order', {}).get('orderId') or result.get('orderId')
                if order_id:
                    validation = self.validate_order(symbol, str(order_id))
                    result['validation'] = validation
            except Exception as e:
                logger.warning(f"Erro na validação automática: {e}")
                result['validation'] = {'error': str(e)}

            return result
            
        except Exception as e:
            logger.error(f"Erro ao colocar ordem: {e}")
            raise

    def get_order_status(self, symbol: str, order_id: str) -> Dict:
        """Consulta status de uma ordem específica"""
        try:
            params = {
                'symbol': symbol,
                'orderId': str(order_id)
            }
            
            result = self._send_signed_request('/openApi/swap/v2/trade/order', params, 'GET')
            return result
            
        except Exception as e:
            logger.error(f"Erro ao consultar ordem {order_id}: {e}")
            return {'status': 'error', 'msg': str(e)}

    def validate_order(self, symbol: str, order_id: str) -> Dict:
        """Valida uma ordem recém-executada"""
        try:
            logger.info(f"Validando ordem {order_id} para {symbol}")
            time.sleep(2)
            
            order_status = self.get_order_status(symbol, order_id)
            
            if 'status' in order_status and order_status['status'] != 'error':
                status = order_status.get('status', 'unknown')
                filled_qty = order_status.get('executedQty', 0)
                avg_price = order_status.get('avgPrice', 0)
                
                validation_result = {
                    'order_id': order_id,
                    'symbol': symbol,
                    'status': status,
                    'filled_quantity': filled_qty,
                    'average_price': avg_price,
                    'validation_time': datetime.now().isoformat(),
                    'success': status in ['FILLED', 'PARTIALLY_FILLED']
                }
                
                logger.info(f"Validação: Status={status}, Qty={filled_qty}, Price={avg_price}")
                return validation_result
                
            else:
                logger.warning("Consulta direta falhou")
                return {
                    'order_id': order_id,
                    'symbol': symbol,
                    'status': 'validation_failed',
                    'success': False
                }
                
        except Exception as e:
            logger.error(f"Erro na validação: {e}")
            return {
                'order_id': order_id,
                'symbol': symbol,
                'status': 'validation_error',
                'error': str(e),
                'success': False
            }

    def _cancel_orders_individually(self, symbol: str) -> Dict:
        """Cancela ordens individualmente como fallback"""
        try:
            open_orders = self.get_open_orders(symbol)
            cancelled_count = 0
            
            for order in open_orders:
                try:
                    order_id = order.orderId
                    if order_id:
                        params = {
                            'symbol': symbol,
                            'orderId': str(order_id)
                        }
                        self._send_signed_request('/openApi/swap/v2/trade/order', params, 'DELETE')
                        cancelled_count += 1
                        time.sleep(0.2)
                        
                except Exception as e:
                    logger.warning(f"Erro ao cancelar ordem individual {order_id}: {e}")
                    continue
            
            logger.info(f"Canceladas {cancelled_count} ordens individualmente em {symbol}")
            return {'success': True, 'cancelled': cancelled_count}
            
        except Exception as e:
            logger.error(f"Erro ao cancelar ordens individuais: {e}")
            return {'success': False, 'error': str(e)}

    def cancel_all_orders(self, symbol: str) -> Dict:
        """CORRIGIDO: Cancela todas as ordens de um símbolo"""
        try:
            open_orders = self.get_open_orders(symbol)
            
            if not open_orders:
                logger.info(f"Nenhuma ordem aberta para cancelar em {symbol}")
                return {'success': True, 'msg': 'No orders to cancel'}
            
            logger.info(f"Cancelando {len(open_orders)} ordens em {symbol}")
            
            try:
                params = {'symbol': symbol}
                result = self._send_signed_request('/openApi/swap/v2/trade/allOpenOrders', params, 'DELETE')
                logger.info(f"Todas as ordens canceladas para {symbol}")
                return result
                
            except Exception as e:
                logger.warning(f"Cancelamento em lote falhou para {symbol}, tentando individual: {e}")
                return self._cancel_orders_individually(symbol)
                
        except Exception as e:
            logger.error(f"Erro ao cancelar ordens para {symbol}: {e}")
            return {'success': False, 'error': str(e)}

    def set_leverage(self, symbol: str, leverage: int, side: str = "BOTH", 
                    position_mode: str = "hedge") -> dict:
        """Define alavancagem para um símbolo - Versão corrigida baseada no teste que funcionou"""
        lev_str = str(leverage)
        
        # Tenta diferentes combinações que funcionaram no teste
        attempts = [
            {"symbol": symbol, "leverage": lev_str, "side": "LONG"},
            {"symbol": symbol, "leverage": lev_str, "side": "SHORT"}, 
            {"symbol": symbol, "leverage": lev_str},  # sem side
            {"symbol": symbol, "leverage": lev_str, "side": "BOTH"}
        ]
        
        last_err = None
        
        for i, params in enumerate(attempts, 1):
            try:
                logger.info(f"Tentativa {i}: {params}")
                result = self._send_signed_request("/openApi/swap/v2/trade/leverage", params, "POST")
                logger.info(f"Leverage definido [{i}/{len(attempts)}]: {symbol} {params.get('side', 'no-side')} -> {leverage}x")
                return result
            except Exception as e:
                logger.debug(f"Tentativa {i} falhou: {e}")
                last_err = e
                time.sleep(0.3)  # Pequena pausa entre tentativas
        
        # Se todas falharam, apenas avisa mas não levanta exceção (leverage pode já estar definido)
        logger.warning(f"Não foi possível definir leverage para {symbol}: {last_err}")
        return {"warning": "Leverage não pôde ser definido, mas ordem pode ainda funcionar"}