# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Copyright contributors to the Leinao project
class TriangulationError(Exception):
    """Base exception for triangulation errors."""


class InputSchemaError(TriangulationError):
    """Raised when the input dataframe schema is invalid."""
