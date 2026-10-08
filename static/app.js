const weightInput = document.querySelector('input[name="weight"]');
const programSelect = document.querySelector('#client-program');
const calorieEstimate = document.querySelector('#calorie-estimate');

function updateCalorieEstimate() {
  const weight = Number.parseFloat(weightInput.value);
  const factor = Number.parseInt(
    programSelect.selectedOptions[0].dataset.calorieFactor,
    10,
  );

  calorieEstimate.textContent = Number.isFinite(weight) && weight > 0
    ? `Estimated daily calories: ${Math.floor(weight * factor)} kcal/day`
    : 'Estimated daily calories: --';
}

weightInput.addEventListener('input', updateCalorieEstimate);
programSelect.addEventListener('change', updateCalorieEstimate);
document.querySelector('.client-form').addEventListener('reset', () => {
  requestAnimationFrame(updateCalorieEstimate);
});
updateCalorieEstimate();