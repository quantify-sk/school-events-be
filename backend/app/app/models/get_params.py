import json
from typing import Dict, List, Optional, Type, Union

from fastapi import HTTPException
from sqlalchemy import Boolean, Date, DateTime
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import Float, Integer, String, and_, asc, cast, desc, or_
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import Query
from sqlalchemy.orm.attributes import InstrumentedAttribute
from app.dependencies import get_base_table_columns


def parse_json_params(
    param_str: str,
) -> Union[Dict[str, Union[str, List[str]]], List[Dict[str, str]]]:
    try:
        param_data = json.loads(param_str)
        if isinstance(param_data, dict):  # For filter_params
            return param_data
        elif isinstance(param_data, list) and all(
            isinstance(item, dict) for item in param_data
        ):  # For sorting_params
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

    if isinstance(column_type, SQLAlchemyEnum):
        enum_values = [e.value for e in column_type.enum_class]
        if value not in enum_values:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid value for {column.name}: {value}, must be one of {enum_values}.",
            )
    elif isinstance(column_type, Integer):
        try:
            int(value)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid value for column {column.name}: {value}, must be an integer.",
            )
    elif isinstance(column_type, String):
        if not isinstance(value, str):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid value for column {column.name}: {value}, must be a string.",
            )
    elif isinstance(column_type, Boolean):
        if value not in ["true", "false"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid value for column {column.name}: {value}, must be 'true' or 'false'.",
            )
    elif isinstance(column_type, Float):
        try:
            float(value)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid value for column {column.name}: {value}, must be a float.",
            )
    elif isinstance(column_type, Date):
        try:
            from datetime import datetime

            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid value for column {column.name}: {value}, must be a date in YYYY-MM-DD format.",
            )
    elif isinstance(column_type, DateTime):
        try:
            from datetime import datetime

            datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid value for column {column.name}: {value}, must be a datetime in YYYY-MM-DDTHH:MM:SS format.",
            )
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
        base_model_columns = get_base_table_columns(model)

        # Add base table columns to column names
        model_columns.update(base_model_columns)

        search_params = params.get("search")

        if search_params:
            if not isinstance(search_params, list):
                raise HTTPException(
                    status_code=400, detail="Search parameter must be a list."
                )

            for _index, search_param in enumerate(search_params):
                if not isinstance(search_param, dict):
                    raise HTTPException(
                        status_code=400,
                        detail="Search parameter must be a dictionary.",
                    )

                term = search_param.get("term")
                columns = search_param.get("columns")
                search_type = search_param.get("type")

                if term is None:
                    raise HTTPException(
                        status_code=400,
                        detail="Search parameter is missing 'term'.",
                    )

                if not isinstance(term, str):
                    raise HTTPException(
                        status_code=400,
                        detail="Search 'term' must be a string.",
                    )

                if columns is None:
                    raise HTTPException(
                        status_code=400,
                        detail="Search parameter is missing 'columns'.",
                    )

                if not isinstance(columns, list):
                    raise HTTPException(
                        status_code=400,
                        detail="Search 'columns' must be a list.",
                    )

                for _col_index, col in enumerate(columns):
                    if not isinstance(col, str):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Search column {col} must be a string.",
                        )
                    if col not in model_columns:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid search column '{col}'.",
                        )

                if search_type is None:
                    raise HTTPException(
                        status_code=400,
                        detail="Search parameter is missing 'type'.",
                    )

                if search_type not in ["AND", "OR"]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid search 'type' value '{search_type}'. Must be 'AND' or 'OR'.",
                    )

        for key, value in params.items():
            if key == "search":
                continue
            if key not in model_columns:
                raise HTTPException(
                    status_code=400, detail=f"Invalid filter column: {key}"
                )

            column = model_columns[key]
            is_nullable = column.nullable

            if isinstance(value, list):
                for v in value:
                    validate_column_type(column, v, is_nullable)
            else:
                validate_column_type(column, value, is_nullable)

    @staticmethod
    def validate_sorting_params(model: Type, params: List[Dict[str, str]]) -> None:
        model_columns = list(model.__table__.columns.keys())
        base_model_columns = get_base_table_columns(model)

        # Add base table columns to column names
        model_columns.extend(base_model_columns.keys())

        # Make set from list
        model_columns = set(model_columns)

        for param in params:
            if not isinstance(param, dict) or len(param) != 1:
                raise HTTPException(
                    status_code=400,
                    detail="Each sorting parameter must be a single key-value pair.",
                )
            column, order = next(iter(param.items()))
            if column not in model_columns:
                raise HTTPException(
                    status_code=400, detail=f"Invalid sorting column: {column}"
                )
            if order not in ["asc", "desc"]:
                raise HTTPException(
                    status_code=400, detail=f"Invalid sorting order: {order}"
                )

    @staticmethod
    def apply_filters_and_sorting(
        query: Query,
        model: Type,
        filter_params: Optional[Dict[str, Union[str, List[str]]]],
        sorting_params: Optional[List[Dict[str, str]]],
    ) -> Query:
        if filter_params:
            if not isinstance(filter_params, dict):
                raise HTTPException(
                    status_code=400, detail="Filter parameter must be a dictionary."
                )

            ParameterValidator.validate_filter_params(model, filter_params)
            search_params = filter_params.get("search", [])
            combined_conditions = []

            for param in search_params:
                term = f"%{param.get('term', '')}%"
                columns = param.get("columns", [])
                conditions = [
                    cast(getattr(model, col), String).ilike(term)
                    for col in columns
                    if col in model.__table__.columns
                ]

                if conditions:
                    # Combine conditions within the search object using OR
                    combined_condition = or_(*conditions)
                    combined_conditions.append(combined_condition)

            # Apply combined conditions according to the overall type between search objects
            if combined_conditions:
                for i in range(len(combined_conditions) - 1):
                    type_next = (
                        search_params[i + 1].get("type", "AND").upper()
                        if i + 1 < len(search_params)
                        else "AND"
                    )
                    if type_next == "AND":
                        combined_conditions[i + 1] = and_(
                            combined_conditions[i], combined_conditions[i + 1]
                        )
                    else:
                        combined_conditions[i + 1] = or_(
                            combined_conditions[i], combined_conditions[i + 1]
                        )

                query = query.filter(combined_conditions[-1])

            # Get column names once
            column_names = list(model.__table__.columns.keys())
            base_model_columns = get_base_table_columns(model)

            # Add base table columns to column names
            column_names.extend(base_model_columns.keys())

            # Make set from list
            column_names = set(column_names)

            # Apply additional direct filters
            for key, value in filter_params.items():
                if key != "search" and key in column_names:
                    column = getattr(model, key, None)
                    if column:
                        if isinstance(value, list):
                            query = query.filter(column.in_(value))
                        else:
                            query = query.filter(column == value)

        if sorting_params:
            if not isinstance(sorting_params, list):
                raise HTTPException(
                    status_code=400, detail="Sorting parameter must be a list."
                )
            ParameterValidator.validate_sorting_params(model, sorting_params)
            for sort_param in sorting_params:
                column, order = next(iter(sort_param.items()))
                if column in model.__table__.columns:
                    query = query.order_by(
                        asc(getattr(model, column))
                        if order == "asc"
                        else desc(getattr(model, column))
                    )
        else:
            # Default sorting by primary key in ascending order
            primary_key_column = model.__table__.primary_key.columns.values()[0].name
            query = query.order_by(asc(getattr(model, primary_key_column)))

        return query
