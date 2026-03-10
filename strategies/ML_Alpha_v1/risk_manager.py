"""
ML Risk Manager v1
==================
Atsakingas už rizikos valdymą ir kapitalo paskirstymą remiantis ML modelio 
prognozių pasitikėjimu (Confidence Score).

Įgyvendina:
1. Dynamic Bet Sizing (Dydžio parinkimas pagal modelio užtikrintumą).
2. Meta-Labeling pamatą (galimybė blokuoti sandorius).
"""

import numpy as np

class MLRiskManager:
    def __init__(self, cash_balance, risk_per_trade=0.02, min_confidence=0.70):
        """
        cash_balance: turimas kapitalas doleriais.
        risk_per_trade: bazinė rizika sandoriui (pvz., 2%).
        min_confidence: minimalus ML pasitikėjimas, kad sandoris būtų vykdomas.
        """
        self.cash_balance = cash_balance
        self.risk_per_trade = risk_per_trade
        self.min_confidence = min_confidence

    def get_position_size(self, price, stop_loss_price, confidence):
        """
        Apskaičiuoja rekomenduojamą pozicijos dydį (Units).
        Naudoja: (Balance * Risk%) / (Price - StopLoss) * Confidence_Factor
        """
        if confidence < self.min_confidence:
            return 0  # Blokuojame sandorį
        
        # 1. Bazinė rizika doleriais (pvz., jei sąskaita 100k, rizika 2% = 2000$)
        risk_amount = self.cash_balance * self.risk_per_trade
        
        # 2. Atstumas iki Stop Loss (rizika vienam unit'ui)
        risk_per_unit = abs(price - stop_loss_price)
        
        if risk_per_unit == 0:
            return 0
            
        # 3. Preliminarus dydis (kiek unit'ų galim nupirkti, kad pasiekus SL prarastume 2000$)
        base_size_units = risk_amount / risk_per_unit
        
        # 4. ML Confidence Factor (suintensyviname arba sumažiname statymą)
        # Normalizuojame confidence iš [0.70, 1.0] į [0.5, 1.5] koeficientą
        conf_range = 1.0 - self.min_confidence
        conf_ratio = (confidence - self.min_confidence) / conf_range
        confidence_multiplier = 0.5 + (conf_ratio * 1.0) # [0.5 - 1.5]
        
        final_size_units = base_size_units * confidence_multiplier
        
        # 5. Kapitalo Check'as (neleidžiame pirkti už daugiau nei turime cash)
        max_units_by_cash = self.cash_balance / price
        final_size_units = min(final_size_units, max_units_by_cash)
        
        return final_size_units

    def validate_setup(self, ml_prediction, confidence, market_regime=None):
        """
        Čia ateityje bus Meta-Labeling logika. 
        Šiuo metu tikrina tik Confidence Threshold.
        """
        if confidence < self.min_confidence:
            return False, "Confidence too low"
            
        return True, "Standard entry approved"
