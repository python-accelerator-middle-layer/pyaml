import functools
import inspect
import warnings
from typing import Type

from pydantic import BaseModel, ValidationError

from ..common.exception import PyAMLConfigException


def validator(model: Type[BaseModel]):
    def decorator(cls):
        # TODO: add check so input model is of right type

        # Add validation model
        cls._validation_model = model

        @classmethod
        def validate(cls, data: dict) -> BaseModel:
            if cls._validation_model is None:
                raise PyAMLConfigException(
                    f"No validation model has been specified for "
                    f"{cls.__module__}.{cls.__name__} so validation is not possible."
                )

            try:
                validated = cls._validation_model(**data)
            except ValidationError as e:
                errors = handle_validation_error(e)
                raise PyAMLConfigException(errors) from None

            return validated

        @classmethod
        def from_validated(cls, data: dict):
            validated = cls.validate(data)
            return cls(**validated.model_dump())

        cls.validate = validate
        cls.from_validated = from_validated

        return cls

    return decorator


def handle_validation_error(e):
    errors = []
    for err in e.errors():
        field = ".".join(str(x) for x in err["loc"])
        errors.append(f"{field}: {err['msg']}")

    return errors
