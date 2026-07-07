// MediCare Hospital Management System - Front-end Logic

document.addEventListener('DOMContentLoaded', function () {
    // 1. Theme Toggle Persistence (Client-Side & Server-Side sync)
    const body = document.body;
    const themeToggleBtn = document.getElementById('theme-toggle');
    
    // Check local storage for theme
    const savedTheme = localStorage.getItem('medicare-theme');
    if (savedTheme === 'dark') {
        body.classList.add('dark-theme');
        updateThemeIcon(true);
    } else {
        body.classList.remove('dark-theme');
        updateThemeIcon(false);
    }
    
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function () {
            const isDark = body.classList.toggle('dark-theme');
            localStorage.setItem('medicare-theme', isDark ? 'dark' : 'light');
            updateThemeIcon(isDark);
            
            // Sync with Flask session asynchronously
            fetch('/toggle-theme')
                .catch(err => console.log('Theme sync error: ', err));
        });
    }
    
    function updateThemeIcon(isDark) {
        if (!themeToggleBtn) return;
        const icon = themeToggleBtn.querySelector('i');
        if (icon) {
            if (isDark) {
                icon.className = 'bi bi-sun-fill';
            } else {
                icon.className = 'bi bi-moon-fill';
            }
        }
    }

    // 2. Mobile Sidebar Toggle
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('show');
        });
    }

    // 3. Dynamic Doctor & Slot Selection (AJAX for Appointment Booking)
    const deptSelect = document.getElementById('department_id');
    const docSelect = document.getElementById('doctor_id');
    const dateInput = document.getElementById('appointment_date');
    const slotSelect = document.getElementById('time_slot');

    if (deptSelect && docSelect) {
        deptSelect.addEventListener('change', function () {
            const deptId = this.value;
            if (!deptId || deptId === '0') {
                docSelect.innerHTML = '<option value="0">Select Doctor</option>';
                return;
            }
            
            docSelect.innerHTML = '<option value="0">Loading doctors...</option>';
            
            fetch(`/patient/api/get-doctors/${deptId}`)
                .then(res => res.json())
                .then(data => {
                    let options = '<option value="0">Select Doctor</option>';
                    data.forEach(doc => {
                        options += `<option value="${doc.id}">${doc.name} (${doc.specialization})</option>`;
                    });
                    docSelect.innerHTML = options;
                    resetSlots();
                })
                .catch(err => {
                    console.error('Fetch doctors error:', err);
                    docSelect.innerHTML = '<option value="0">Error loading doctors</option>';
                });
        });
    }

    if (docSelect && dateInput && slotSelect) {
        const updateSlots = function () {
            const docId = docSelect.value;
            const apptDate = dateInput.value;
            
            if (!docId || docId === '0' || !apptDate) {
                resetSlots();
                return;
            }
            
            // Set loading state
            const originalOptions = Array.from(slotSelect.options);
            slotSelect.innerHTML = '<option value="">Loading available slots...</option>';
            
            fetch(`/patient/api/get-booked-slots/${docId}/${apptDate}`)
                .then(res => res.json())
                .then(bookedSlots => {
                    // Reset dropdown choices
                    slotSelect.innerHTML = '';
                    
                    originalOptions.forEach(opt => {
                        const optionValue = opt.value;
                        if (optionValue === '') {
                            slotSelect.appendChild(opt);
                            return;
                        }
                        
                        // Disable if already booked
                        if (bookedSlots.includes(optionValue)) {
                            const newOpt = opt.cloneNode(true);
                            newOpt.disabled = true;
                            newOpt.text = `${optionValue} (Booked)`;
                            slotSelect.appendChild(newOpt);
                        } else {
                            opt.disabled = false;
                            opt.text = optionValue;
                            slotSelect.appendChild(opt.cloneNode(true));
                        }
                    });
                })
                .catch(err => {
                    console.error('Fetch slots error:', err);
                    resetSlots();
                });
        };

        docSelect.addEventListener('change', updateSlots);
        dateInput.addEventListener('change', updateSlots);
    }

    function resetSlots() {
        if (slotSelect) {
            Array.from(slotSelect.options).forEach(opt => {
                opt.disabled = false;
                if (opt.value !== '') {
                    opt.text = opt.value;
                }
            });
        }
    }

    // 4. Dynamic Prescription Medicines Builder
    const addMedBtn = document.getElementById('add-medicine-btn');
    const medContainer = document.getElementById('medicine-container');
    
    if (addMedBtn && medContainer) {
        let medIndex = medContainer.querySelectorAll('.med-row').length;
        
        addMedBtn.addEventListener('click', function () {
            const row = document.createElement('div');
            row.className = 'med-row animated-fade position-relative';
            row.innerHTML = `
                <button type="button" class="btn-close position-absolute top-0 end-0 m-2 remove-med-btn" aria-label="Close"></button>
                <div class="row g-3">
                    <div class="col-md-5">
                        <label class="form-label font-weight-bold">Medicine Name</label>
                        <input type="text" name="medicine_name[]" class="form-control" placeholder="e.g. Paracetamol 650mg" required>
                    </div>
                    <div class="col-md-5 d-flex align-items-center">
                        <div class="mt-4">
                            <div class="form-check form-check-inline">
                                <input type="checkbox" name="med_${medIndex}_morning" id="med_${medIndex}_morning" class="form-check-input">
                                <label for="med_${medIndex}_morning" class="form-check-label">Morning</label>
                            </div>
                            <div class="form-check form-check-inline">
                                <input type="checkbox" name="med_${medIndex}_afternoon" id="med_${medIndex}_afternoon" class="form-check-input">
                                <label for="med_${medIndex}_afternoon" class="form-check-label">Afternoon</label>
                            </div>
                            <div class="form-check form-check-inline">
                                <input type="checkbox" name="med_${medIndex}_night" id="med_${medIndex}_night" class="form-check-input">
                                <label for="med_${medIndex}_night" class="form-check-label">Night</label>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label font-weight-bold">Duration (Days)</label>
                        <input type="number" name="duration_days[]" class="form-control" min="1" value="5" required>
                    </div>
                </div>
            `;
            
            medContainer.appendChild(row);
            medIndex++;
            
            // Re-apply close handler
            row.querySelector('.remove-med-btn').addEventListener('click', function () {
                row.remove();
            });
        });
        
        // Add remove handlers to existing rows
        medContainer.querySelectorAll('.remove-med-btn').forEach(btn => {
            btn.addEventListener('click', function () {
                btn.closest('.med-row').remove();
            });
        });
    }

    // 5. Dashboard Charts initialization using Chart.js
    const apptCtx = document.getElementById('appointmentChart');
    const revCtx = document.getElementById('revenueChart');
    const growthCtx = document.getElementById('patientGrowthChart');
    const perfCtx = document.getElementById('doctorPerformanceChart');
    
    if (apptCtx || revCtx || growthCtx || perfCtx) {
        fetch('/admin/api/dashboard-charts')
            .then(res => res.json())
            .then(data => {
                // Determine theme-specific labels & grid colors
                const isDarkTheme = body.classList.contains('dark-theme');
                const gridColor = isDarkTheme ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.05)';
                const labelColor = isDarkTheme ? '#94a3b8' : '#64748b';

                const commonOptions = {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { labels: { color: labelColor, font: { family: 'Outfit' } } }
                    },
                    scales: {
                        x: { grid: { color: gridColor }, ticks: { color: labelColor, font: { family: 'Outfit' } } },
                        y: { grid: { color: gridColor }, ticks: { color: labelColor, font: { family: 'Outfit' } } }
                    }
                };

                // Chart 1: Appointments per month
                if (apptCtx) {
                    new Chart(apptCtx, {
                        type: 'line',
                        data: {
                            labels: data.months,
                            datasets: [{
                                label: 'Appointments Booked',
                                data: data.appointments,
                                borderColor: '#0d6efd',
                                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                                fill: true,
                                tension: 0.3
                            }]
                        },
                        options: commonOptions
                    });
                }

                // Chart 2: Revenue Chart (Stacked breakdown)
                if (revCtx) {
                    new Chart(revCtx, {
                        type: 'bar',
                        data: {
                            labels: data.months,
                            datasets: [
                                {
                                    label: 'Consultation Fees',
                                    data: data.consultation_revenue,
                                    backgroundColor: '#0d6efd',
                                },
                                {
                                    label: 'Pharmacy Revenue',
                                    data: data.pharmacy_revenue,
                                    backgroundColor: '#f59e0b',
                                },
                                {
                                    label: 'Laboratory Revenue',
                                    data: data.lab_revenue,
                                    backgroundColor: '#10b981',
                                }
                            ]
                        },
                        options: {
                            ...commonOptions,
                            scales: {
                                x: { ...commonOptions.scales.x, stacked: true },
                                y: { ...commonOptions.scales.y, stacked: true }
                            }
                        }
                    });
                }

                // Chart 3: Patient Growth Chart
                if (growthCtx) {
                    new Chart(growthCtx, {
                        type: 'line',
                        data: {
                            labels: data.months,
                            datasets: [{
                                label: 'New Patient Registrations',
                                data: data.patient_growth,
                                borderColor: '#f59e0b',
                                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                                fill: true,
                                tension: 0.3
                            }]
                        },
                        options: commonOptions
                    });
                }

                // Chart 4: Doctor Performance
                if (perfCtx) {
                    new Chart(perfCtx, {
                        type: 'doughnut',
                        data: {
                            labels: data.doctor_performance.labels,
                            datasets: [{
                                data: data.doctor_performance.data,
                                backgroundColor: [
                                    '#0d6efd', '#10b981', '#f59e0b', '#ef4444', 
                                    '#8b5cf6', '#ec4899', '#06b6d4', '#14b8a6'
                                ],
                                borderWidth: 0
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'bottom',
                                    labels: { color: labelColor, font: { family: 'Outfit', size: 11 } }
                                }
                            }
                        }
                    });
                }
            })
            .catch(err => console.error('Error loading chart data:', err));
    }
});
