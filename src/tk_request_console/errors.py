from __future__ import annotations


class AppError(Exception):
    pass


class ConfigError(AppError):
    pass


class TokenError(AppError):
    pass


class TemplateError(AppError):
    pass


class ProfileError(AppError):
    pass


class TransportError(AppError):
    def __init__(self, message: str, url: str):
        super().__init__(message)
        self.url = url
