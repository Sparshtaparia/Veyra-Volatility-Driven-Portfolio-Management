"""
backend/exceptions.py
=====================
Domain and application specific exceptions.
"""

class PortfolioNotFoundError(Exception):
    def __init__(self, portfolio_id: str):
        self.portfolio_id = portfolio_id
        super().__init__(f"Portfolio not found: {portfolio_id}")

class EvaluationNotFoundError(Exception):
    def __init__(self, evaluation_id: str):
        self.evaluation_id = evaluation_id
        super().__init__(f"Evaluation not found: {evaluation_id}")

class InvalidPortfolioError(Exception):
    def __init__(self, message: str):
        super().__init__(message)

class InvalidEvaluationError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
