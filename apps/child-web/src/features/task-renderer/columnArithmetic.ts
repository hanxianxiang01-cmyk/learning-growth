export type ColumnPlace = "ones" | "tens" | "hundreds" | "thousands";

export type ColumnDigit = {
  place: ColumnPlace;
  value: number | null;
};

export type CarryEntry = {
  from_place: ColumnPlace;
  to_place: ColumnPlace;
  value: 0 | 1;
};

export type ColumnArithmeticState = {
  result_digits: ColumnDigit[];
  carries: CarryEntry[];
};

export type ColumnArithmeticConfig = {
  operands: number[];
  places: ColumnPlace[];
  operand_layout?: "fixed" | "right_aligned";
};

export type ColumnArithmeticResponse = {
  result_digits: ColumnDigit[];
  carries: CarryEntry[];
};

const PLACE_INDEX: Record<ColumnPlace, number> = {
  ones: 0,
  tens: 1,
  hundreds: 2,
  thousands: 3
};

export function placePower(place: ColumnPlace): number {
  return 10 ** PLACE_INDEX[place];
}

export function getDigit(value: number, place: ColumnPlace): number {
  return Math.floor(Math.abs(value) / placePower(place)) % 10;
}

export function expectedResult(config: ColumnArithmeticConfig): number {
  return config.operands.reduce((sum, value) => sum + value, 0);
}

export function expectedDigits(config: ColumnArithmeticConfig): ColumnDigit[] {
  const result = expectedResult(config);
  return config.places.map(place => ({
    place,
    value: getDigit(result, place)
  }));
}

export function expectedCarries(config: ColumnArithmeticConfig): CarryEntry[] {
  const carries: CarryEntry[] = [];
  const places = config.places;
  for (let index = 0; index < places.length - 1; index += 1) {
    const place = places[index];
    const sum = config.operands.reduce((total, operand) => total + getDigit(operand, place), 0);
    if (sum >= 10) {
      carries.push({
        from_place: place,
        to_place: places[index + 1],
        value: 1
      });
    }
  }
  return carries;
}

export function initialColumnArithmeticState(
  config: ColumnArithmeticConfig,
  initialState?: Partial<ColumnArithmeticState>
): ColumnArithmeticState {
  return {
    result_digits: config.places.map(place => {
      const found = initialState?.result_digits?.find(item => item.place === place);
      return { place, value: found?.value ?? null };
    }),
    carries: config.places.slice(0, -1).map(place => {
      const found = initialState?.carries?.find(item => item.from_place === place);
      return {
        from_place: place,
        to_place: config.places[config.places.indexOf(place) + 1],
        value: found?.value === 1 ? 1 : 0
      };
    })
  };
}

export function setResultDigit(
  state: ColumnArithmeticState,
  place: ColumnPlace,
  value: number | null
): ColumnArithmeticState {
  return {
    ...state,
    result_digits: state.result_digits.map(item =>
      item.place === place ? { ...item, value } : item
    )
  };
}

export function toggleCarry(
  state: ColumnArithmeticState,
  fromPlace: ColumnPlace
): ColumnArithmeticState {
  return {
    ...state,
    carries: state.carries.map(item =>
      item.from_place === fromPlace
        ? { ...item, value: item.value === 1 ? 0 : 1 }
        : item
    )
  };
}

export function numericAnswer(state: ColumnArithmeticState): number | null {
  const filled = state.result_digits.filter(item => item.value !== null);
  if (filled.length !== state.result_digits.length) return null;
  return state.result_digits.reduce(
    (sum, item) => sum + (item.value ?? 0) * placePower(item.place),
    0
  );
}

export type ColumnArithmeticEvaluation = {
  status: "PASS" | "PARTIAL" | "FAIL" | "INVALID";
  answer: number | null;
  expected_answer: number;
  incorrect_places: ColumnPlace[];
  incorrect_carries: ColumnPlace[];
};

export function evaluateColumnArithmetic(
  config: ColumnArithmeticConfig,
  state: ColumnArithmeticState
): ColumnArithmeticEvaluation {
  const expected = expectedDigits(config);
  const expectedCarry = expectedCarries(config);
  const answer = numericAnswer(state);

  const invalidDigit = state.result_digits.some(
    item => item.value !== null && (!Number.isInteger(item.value) || item.value < 0 || item.value > 9)
  );
  if (invalidDigit) {
    return {
      status: "INVALID",
      answer,
      expected_answer: expectedResult(config),
      incorrect_places: [],
      incorrect_carries: []
    };
  }

  const incorrectPlaces = expected
    .filter(item => {
      const actual = state.result_digits.find(value => value.place === item.place)?.value;
      return actual !== null && actual !== undefined && actual !== item.value;
    })
    .map(item => item.place);

  const incorrectCarries = state.carries
    .filter(actual => {
      const expectedValue =
        expectedCarry.find(item => item.from_place === actual.from_place)?.value ?? 0;
      return actual.value === 1 && expectedValue === 0;
    })
    .map(item => item.from_place);

  const unfilledDigits = state.result_digits.some(item => item.value === null);
  const unfilledExpectedCarries = expectedCarry.some(expectedItem =>
    state.carries.find(value => value.from_place === expectedItem.from_place)?.value !== expectedItem.value
  );

  if (incorrectPlaces.length === 0 && incorrectCarries.length === 0 && answer === expectedResult(config)) {
    return {
      status: "PASS",
      answer,
      expected_answer: expectedResult(config),
      incorrect_places: [],
      incorrect_carries: []
    };
  }

  if (
    incorrectPlaces.length === 0 &&
    incorrectCarries.length === 0 &&
    (unfilledDigits || unfilledExpectedCarries)
  ) {
    return {
      status: "PARTIAL",
      answer,
      expected_answer: expectedResult(config),
      incorrect_places: [],
      incorrect_carries: []
    };
  }

  return {
    status: "FAIL",
    answer,
    expected_answer: expectedResult(config),
    incorrect_places: incorrectPlaces,
    incorrect_carries: incorrectCarries
  };
}

export function serializeColumnArithmetic(
  state: ColumnArithmeticState
): ColumnArithmeticResponse {
  return {
    result_digits: state.result_digits.map(item => ({ ...item })),
    carries: state.carries.map(item => ({ ...item }))
  };
}
