import json
from datetime import datetime
from typing import Dict, List, Optional, Type, Union

from app.dependencies import get_base_table_columns
from fastapi import HTTPException
from sqlalchemy import Boolean, Date, DateTime
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import Float, Integer, String, and_, asc, cast, desc, or_
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import Query
from sqlalchemy.orm.attributes import InstrumentedAttribute


def parse_json_params(
    param_str: str,
) -> Union[Dict[str, Union[str, List[str]]], List[Dict[str, str]]]:
    try:
        param_data = json.loads(param_str)
        if isinstance(param_data, dict):
            return param_data
        elif isinstance(param_data, list) and all(
            isinstance(item, dict) for item in param_data
        ):
            return param_data
        else:
            raise ValueError("Invalid parameters format.")
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid parameters: {e}")


def validate_column_type(column: InstrumentedAttribute, value: str, is_nullable: bool):
    column_type = column.type

    if value is None:
        if not is_nullable:
            raise HTTPException(
                status_code=400, detail=f"Column {column.name} cannot be null."
            )
        return

    type_checkers = {
        SQLAlchemyEnum: lambda v: v in [e.value for e in column_type.enum_class],
        Integer: lambda v: isinstance(int(v), int),
        String: lambda v: isinstance(v, str),
        Boolean: lambda v: v in ["true", "false"],
        Float: lambda v: isinstance(float(v), float),
        Date: lambda v: datetime.strptime(v, "%Y-%m-%d"),
        DateTime: lambda v: datetime.strptime(v, "%Y-%m-%dT%H:%M:%S"),
    }

    for sql_type, checker in type_checkers.items():
        if isinstance(column_type, sql_type):
            try:
                if not checker(value):
                    raise ValueError()
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid value for column {column.name}: {value}.",
                )
            break
    else:
        raise HTTPException(
            status_code=400, detail=f"Unsupported column type for column {column.name}."
        )


class ParameterValidator:
    @staticmethod
    def validate_filter_params(
        model: Type[DeclarativeMeta], params: Dict[str, Union[str, List[str]]]
    ) -> None:
        model_columns = {col.name: col for col in model.__table__.columns}
        model_columns.update(get_base_table_columns(model))

        def validate_search_param(search_param: Dict[str, Union[str, List[str]]]):
            term = search_param.get("term")
            columns = search_param.get("columns")
            search_type = search_param.get("type")

            if (
                not isinstance(term, str)
                or not isinstance(columns, list)
                or search_type not in ["AND", "OR"]
            ):
                raise HTTPException(status_code=400, detail="Invalid search parameter.")

            for col in columns:
                if col not in model_columns:
                    raise HTTPException(
                        status_code=400, detail=f"Invalid search column '{col}'."
                    )

        def validate_multi_column_filter(
            multi_column_filter: List[Dict[str, Union[List[str], List[int]]]]
        ):
            if not isinstance(multi_column_filter, list):
                raise HTTPException(
                    status_code=400, detail="Invalid multi-column filter format."
                )

            for column_entry in multi_column_filter:
                if not isinstance(column_entry, dict):
                    raise HTTPException(
                        status_code=400,
                        detail="Each entry in 'multi_columns' must be a dictionary.",
                    )

                for column_name, values in column_entry.items():
                    if not isinstance(values, list):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid values for column '{column_name}'.",
                        )

                    if column_name not in model_columns:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid column '{column_name}' for table.",
                        )

                    for value in values:
                        validate_column_type(
                            model_columns[column_name],
                            value,
                            model_columns[column_name].nullable,
                        )

        # Validate search parameters
        search_params = params.get("search", [])
        if search_params and isinstance(search_params, list):
            for search_param in search_params:
                validate_search_param(search_param)

        # Validate multi-column filter parameters
        multi_column_filter = params.get("multi_columns", [])
        if multi_column_filter:
            validate_multi_column_filter(multi_column_filter)

        # Validate other filters
        for key, value in params.items():
            if key in ["search", "multi_columns"]:
                continue
            if key not in model_columns:
                raise HTTPException(
                    status_code=400, detail=f"Invalid filter column: {key}"
                )

            column = model_columns[key]
            if isinstance(value, list):
                for v in value:
                    validate_column_type(column, v, column.nullable)
            else:
                validate_column_type(column, value, column.nullable)

    @staticmethod
    def validate_sorting_params(model: Type, params: List[Dict[str, str]]) -> None:
        model_columns = set(model.__table__.columns.keys()).union(
            get_base_table_columns(model)
        )

        for param in params:
            if not isinstance(param, dict) or len(param) != 1:
                raise HTTPException(
                    status_code=400,
                    detail="Each sorting parameter must be a single key-value pair.",
                )
            column, order = next(iter(param.items()))
            if column not in model_columns or order not in ["asc", "desc"]:
                raise HTTPException(
                    status_code=400, detail="Invalid sorting parameter."
                )

    @staticmethod
    def apply_filters_and_sorting(
        query: Query,
        model: Type,
        filter_params: Optional[Dict[str, Union[str, List[str]]]],
        sorting_params: Optional[List[Dict[str, str]]],
    ) -> Query:
        if filter_params:
            ParameterValidator.validate_filter_params(model, filter_params)
            search_params = filter_params.get("search", [])
            combined_conditions = []

            # Process multi-column filter
            multi_column_filter = filter_params.get("multi_columns", [])
            if multi_column_filter:
                or_conditions = []

                for column_entry in multi_column_filter:
                    and_conditions = []

                    for column_name, values in column_entry.items():
                        if column_name not in model.__table__.columns:
                            continue
                        column = getattr(model, column_name)
                        and_conditions.append(column.in_(values))

                    if and_conditions:
                        or_conditions.append(and_(*and_conditions))

                if or_conditions:
                    combined_conditions.append(or_(*or_conditions))

            # Process normal search parameters
            for param in search_params:
                term = f"%{param.get('term', '')}%"
                conditions = [
                    cast(getattr(model, col), String).ilike(term)
                    for col in param.get("columns", [])
                    if col in model.__table__.columns
                ]

                if conditions:
                    combined_conditions.append(or_(*conditions))

            if combined_conditions:
                for i in range(len(combined_conditions) - 1):
                    next_type = (
                        search_params[i + 1].get("type", "AND").upper()
                        if i + 1 < len(search_params)
                        else "AND"
                    )
                    combined_conditions[i + 1] = (
                        and_(combined_conditions[i], combined_conditions[i + 1])
                        if next_type == "AND"
                        else or_(combined_conditions[i], combined_conditions[i + 1])
                    )
                query = query.filter(combined_conditions[-1])

            # Apply additional direct filters
            for key, value in filter_params.items():
                if (
                    key not in ["search", "multi_columns"]
                    and key in model.__table__.columns
                ):
                    column = getattr(model, key)
                    query = query.filter(
                        column.in_(value)
                        if isinstance(value, list)
                        else column == value
                    )

        if sorting_params:
            ParameterValidator.validate_sorting_params(model, sorting_params)
            for sort_param in sorting_params:
                column, order = next(iter(sort_param.items()))
                query = query.order_by(
                    asc(getattr(model, column))
                    if order == "asc"
                    else desc(getattr(model, column))
                )
        else:
            primary_key_column = model.__table__.primary_key.columns.values()[0].name
            query = query.order_by(asc(getattr(model, primary_key_column)))

        return query
