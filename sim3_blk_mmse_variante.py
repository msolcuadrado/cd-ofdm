# -*- coding: utf-8 -*-
"""
Created on Sat Mar  2 15:59:31 2024

@author: 
"""
#%% Inicializar sim
import numpy as np
import QAM16 as qam
import channels
import math
import utils

sz = lambda x: (np.size(x,0), np.size(x,1))

N = 128 # numero de subportadoras
pilot_period = 8 # un piloto cada esta cantidad de simbolos
QAM_symb_len = N*1000 # cantidad de simbolos QAM a transmitir
CP = N // 4 # prefijo ciclico
SNR = 30 #dB

# Para siempre generar los mimsos numeros aleatorios y tener repetibilidad
np.random.seed(1234)

#  Simbolos
Nbits = QAM_symb_len*qam.QAM_bits_per_symbol
data_bits = np.random.randint(2,size=Nbits)

# Convierto la serie de bits a una serie de simbolos qam
data_qam = qam.bits_to_qam(data_bits)

# Conversion serie a paralelo
data_par = data_qam.reshape(N, -1)

# Agrego pilotos (en la frecuencia, todos unos)
all_symb, pilot_symbol = utils.add_block_pilots(data_par, amplitude=qam.QAM(0), period=pilot_period)

#%% Convierto a ODFM
import ofdm
#tx_symb = ofdm.mod(all_symb)
#tx_pilot = ofdm.mod(all_symb[:,0])

#%% Canal
H = channels.fadding_channel(N) #Canal en frecuencia
# Prealoco matriz con simbolos recibidos
rx_symb = np.zeros(all_symb.shape, dtype=all_symb.dtype)

# Calculo de la varianza del ruido
# SNR = 10.log(P_S/P_N)
# 10^(SNR/10) = var(symb_QAM)/var(N)
# var(N) = var(symb_QAM)/10^(SNR/10)
var_noise = qam.eps/pow(10, SNR/10)

for idx in range(0,rx_symb.shape[1]):
    # Vario levemente el canal (canal variante en el tiempo AR-1)
    H = 0.99*H + 0.01*channels.fadding_channel(N)
    ofdm_noise = math.sqrt(var_noise)*np.random.standard_normal(size=N)
    rx_ofdm = all_symb[:,idx]*H + ofdm_noise
    rx_symb[:,idx] = ofdm.mod(rx_ofdm)

#%% Recepcion
Nport = np.size(rx_symb, axis=0)
N_rx = np.size(rx_symb, axis=1)
Npilots_rx = (np.size(rx_symb, axis=1)//8) +1
Ndata_rx = N_rx-Npilots_rx

# Prealoco filtro inverso y lo pongo plano
HMMSE = np.zeros((Nport,1), dtype=rx_symb.dtype)
# Prealoco matriz para los simbolos ofdm recuperados
rx_fix_symb = np.zeros((Nport,Ndata_rx), dtype=rx_symb.dtype)

rx_freq = ofdm.demod(rx_symb)

d_idx = 0
N0 = var_noise # TODO: ESTO DEBE ESTAR MAL CALCULADO
#SNR_MFB = qam.eps / N0
for idx in range(0,N_rx):
    # Si es un multiplo de pilot_period, es un piloto
    if idx%pilot_period == 0:
        #Estimacion canal LS, y lo invierto
        Y = rx_freq[:,idx]
        # Armo una matriz H tal que Y = H X + n, donde X,Y son simbolos ofdm
        #H=np.diag(np.divide(Y, pilot_symbol))
        #W_mmse = H.T.conj() @ np.linalg.inv((H @ H.T.conj()) + N0 * np.eye(N))
        H=np.divide(Y, pilot_symbol)
        # adaptado de https://www.sharetechnote.com/html/Communication_ChannelModel_MMSE.html
        W_mmse=np.diag(H.conj()/((abs(H)**2)+N0))
    else:
        rx_fix_symb[:,d_idx] = W_mmse @ rx_freq[:,idx] #MMSE
        #rx_fix_symb[:,d_idx] = rx_freq[:,idx] / H #LS
        d_idx = d_idx +1

# obtengo bits
rx_bits = qam.qam_to_bits(rx_fix_symb.reshape(-1))

# Calculo errores
Nerr = np.sum(rx_bits != data_bits)
Perr = Nerr / np.size(data_bits)

print(f"""Prob errrores: {Perr*100}%""")

#%% graficos
qam.plot_qam_constellation(rx_fix_symb)