// Add this at the top of the file
const GATEWAY_URL = window.CONFIG.GATEWAY_URL || 'http://localhost:5001';
const BACKEND_URL = 'http://localhost:5002';  // Updated to match the backend port

// Initialize Socket.IO connection
const socket = io();

// DOM Elements
const messagesContainer = document.getElementById('chat-messages');
const bookingDetails = document.getElementById('booking-details');
const bookingDate = document.getElementById('booking-date');
const bookingVisitors = document.getElementById('booking-visitors');
const bookingAmount = document.getElementById('booking-amount');
const paymentSection = document.getElementById('payment-section');
const proceedPaymentBtn = document.getElementById('proceed-payment');
const confirmedBookingDetails = document.getElementById('confirmed-booking-details');
const confirmedBookingId = document.getElementById('confirmed-booking-id');
const confirmedBookingDate = document.getElementById('confirmed-booking-date');
const confirmedBookingVisitors = document.getElementById('confirmed-booking-visitors');
const confirmedBookingAmount = document.getElementById('confirmed-booking-amount');

// Booking state
let currentBooking = {
    date: null,
    nationality: null,
    adults: 0,
    children: 0,
    ticketType: null,
    timeSlot: null,
    amount: 0,
    adultPrice: 0,
    childPrice: 0,
    email: null
};

// Connect to WebSocket
socket.on('connect', () => {
    console.log('Connected to server');
    showWelcomeMessage();
});

function showWelcomeMessage() {
    addMessage('Welcome to the Museum Ticket Booking System! How can I help you today?', 'bot');
    showInitialOptions();
}

function showInitialOptions() {
    const options = [
        { text: 'Book Tickets', icon: 'bi-ticket-perforated', action: 'start_booking' },
        { text: 'View Calendar', icon: 'bi-calendar3', action: 'show_calendar' },
        { text: 'Check Booking Status', icon: 'bi-search', action: 'check_status' }
    ];
    
    const quickReplies = document.createElement('div');
    quickReplies.className = 'quick-replies';
    
    options.forEach(option => {
        const button = document.createElement('button');
        button.className = 'quick-reply-btn';
        button.innerHTML = `<i class="bi ${option.icon}"></i> ${option.text}`;
        button.onclick = () => handleInitialOption(option.action);
        quickReplies.appendChild(button);
    });
    
    messagesContainer.appendChild(quickReplies);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function handleInitialOption(action) {
    switch (action) {
        case 'start_booking':
            addMessage('Let\'s start your booking! First, please select a date for your visit.', 'bot');
            showCalendar();
            break;
        case 'show_calendar':
            addMessage('Here\'s our availability calendar:', 'bot');
            showCalendar();
            break;
        case 'check_status':
            showBookingStatus();
            break;
    }
}

// Handle incoming messages
socket.on('response', (data) => {
    addMessage(data.message, 'bot');
    
    if (data.action) {
        handleBotAction(data.action);
    }
});

socket.on('error', (data) => {
    addMessage('Sorry, an error occurred: ' + data.message, 'bot error');
});

// Handle bot actions
function handleBotAction(action) {
    switch (action) {
        case 'show_calendar':
            showCalendar();
            break;
        case 'select_nationality':
            showNationalityOptions();
            break;
        case 'select_visitors':
            showVisitorInputs();
            break;
        case 'select_time':
            showTimeSlots();
            break;
        case 'show_summary':
            updateBookingSummary();
            break;
    }
}

// Add message to chat
function addMessage(message, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    
    // Check if message is HTML content
    if (typeof message === 'string' && message.trim().startsWith('<')) {
        bubble.innerHTML = message;
    } else {
        bubble.textContent = message;
    }
    
    messageDiv.appendChild(bubble);
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Initialize calendar variables
let currentMonth = new Date().getMonth();
let currentYear = new Date().getFullYear();

// Calendar functions
function showCalendar() {
    const calendarModal = document.getElementById('calendarModal');
    
    // Initialize modal if not already done
    let modal = bootstrap.Modal.getInstance(calendarModal);
    if (!modal) {
        modal = new bootstrap.Modal(calendarModal);
    }
    modal.show();
    
    // Create calendar UI
    const calendar = document.getElementById('calendar');
    calendar.innerHTML = '';
    
    // Create month selector
    const monthSelector = document.createElement('div');
    monthSelector.className = 'month-selector d-flex justify-content-between align-items-center mb-3';
    monthSelector.innerHTML = `
        <button class="btn btn-outline-primary" onclick="changeMonth(-1)">&lt; Prev</button>
        <h4>${getMonthName(currentMonth)} ${currentYear}</h4>
        <button class="btn btn-outline-primary" onclick="changeMonth(1)">Next &gt;</button>
    `;
    calendar.appendChild(monthSelector);
    
    // Create calendar grid
    const gridHtml = createCalendarGrid(currentYear, currentMonth);
    calendar.insertAdjacentHTML('beforeend', gridHtml);
    
    // Add click event listeners to all date cells
    calendar.querySelectorAll('td[data-date]').forEach(cell => {
        if (!cell.classList.contains('disabled')) {
            cell.addEventListener('click', () => {
                const dateStr = cell.getAttribute('data-date');
                if (dateStr) {
                    selectDate(dateStr);
                }
            });
        }
    });
    
    // Fetch and update availability data
    fetchCalendarData(currentYear, currentMonth + 1);
}

function getMonthName(month) {
    const months = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December'];
    return months[month];
}

function createCalendarGrid(year, month) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startingDay = firstDay.getDay();
    const monthLength = lastDay.getDate();
    
    let html = '<table class="calendar table table-bordered">';
    html += '<thead><tr>';
    ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].forEach(day => {
        html += `<th>${day}</th>`;
    });
    html += '</tr></thead><tbody>';
    
    let day = 1;
    for (let i = 0; i < 6; i++) {
        html += '<tr>';
        for (let j = 0; j < 7; j++) {
            if (i === 0 && j < startingDay) {
                html += '<td></td>';
            } else if (day > monthLength) {
                html += '<td></td>';
            } else {
                const currentDate = new Date(year, month, day);
                const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                
                let classes = ['calendar-day'];
                
                // Check if date is in the past
                if (currentDate < today) {
                    classes.push('past disabled');
                } else if (currentDate.getTime() === today.getTime()) {
                    classes.push('today');
                } else {
                    classes.push('future');
                }
                
                html += `<td class="${classes.join(' ')}" data-date="${dateStr}">
                    <div class="date-number">${day}</div>
                    <div class="slots">Loading...</div>
                </td>`;
                day++;
            }
        }
        html += '</tr>';
        if (day > monthLength) {
            break;
        }
    }
    html += '</tbody></table>';
    return html;
}

function selectDate(dateStr) {
    if (!dateStr) return;
    
    currentBooking.date = dateStr;
    
    // Update UI to show selected date
    document.querySelectorAll('.calendar td').forEach(cell => {
        cell.classList.remove('selected');
    });
    
    const selectedCell = document.querySelector(`td[data-date="${dateStr}"]`);
    if (selectedCell) {
        selectedCell.classList.add('selected');
    }
    
    // Close calendar modal and proceed with booking
    const modal = bootstrap.Modal.getInstance(document.getElementById('calendarModal'));
    if (modal) {
        modal.hide();
    }
    
    // Display selected date in chat
    const formattedDate = new Date(dateStr).toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    addMessage(`You selected: ${formattedDate}`, 'user');
    
    addMessage('Are you a local or international visitor?', 'bot');
    showNationalityOptions();
}

function changeMonth(delta) {
    currentMonth += delta;
    
    if (currentMonth > 11) {
        currentMonth = 0;
        currentYear++;
    } else if (currentMonth < 0) {
        currentMonth = 11;
        currentYear--;
    }
    
    showCalendar();
}

// Booking functions
function showNationalityOptions() {
    const options = ['Local', 'Foreign'];  // Updated to match backend
    const quickReplies = document.createElement('div');
    quickReplies.className = 'quick-replies';
    
    options.forEach(option => {
        const button = document.createElement('button');
        button.className = 'quick-reply-btn';
        button.textContent = option;
        button.onclick = () => selectNationality(option);
        quickReplies.appendChild(button);
    });
    
    messagesContainer.appendChild(quickReplies);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function selectNationality(nationality) {
    currentBooking.nationality = nationality;
    
    // Remove nationality options
    const quickReplies = document.querySelector('.quick-replies');
    if (quickReplies) {
        quickReplies.remove();
    }
    
    addMessage(`Selected nationality: ${nationality}`, 'user');
    addMessage('Please select your preferred ticket type:', 'bot');
    showTicketTypes();
}

async function fetchPricing() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/pricing?nationality=${currentBooking.nationality}&ticketType=${currentBooking.ticketType}&date=${currentBooking.date}`);
        if (!response.ok) throw new Error('Failed to fetch pricing');
        const pricing = await response.json();
        return pricing;
    } catch (error) {
        console.error('Error fetching pricing:', error);
        return null;
    }
}

async function showVisitorInputs() {

    const inputsHtml = `
        <div class="visitor-inputs">
            <div class="form-group">
                <label for="adults-input">Number of Adults:</label>
                <input type="number" id="adults-input" min="1" value="1" required>
            </div>
            <div class="form-group">
                <label for="children-input">Number of Children:</label>
                <input type="number" id="children-input" min="0" value="0" required>
            </div>
            <button onclick="submitVisitors()">Continue</button>
        </div>
    `;
    // First fetch the pricing information
    try {
        const response = await fetch(`${BACKEND_URL}/api/pricing?nationality=${currentBooking.nationality}&ticketType=${currentBooking.ticketType}&date=${currentBooking.date}`);
        if (!response.ok) throw new Error('Failed to fetch pricing');
        const pricing = await response.json();
        
        // Add pricing information as a bot message with ₹ symbol
        addMessage(`Ticket Prices:\nAdult: ₹${pricing.adult_price}\nChild: ₹${pricing.child_price}`, 'bot');
    } catch (error) {
        console.error('Error fetching pricing:', error);
    }

    // Show the input fields
    const inputs = document.createElement('div');
    inputs.className = 'visitor-inputs';
    inputs.innerHTML = `
        <div class="mb-3">
            <label>Number of Adults:</label>
            <input type="number" min="1" value="1" class="form-control" id="adults-input">
        </div>
        <div class="mb-3">
            <label>Number of Children:</label>
            <input type="number" min="0" value="0" class="form-control" id="children-input">
        </div>
        <button class="btn btn-primary" onclick="submitVisitors()">Continue</button>
    `;
    const messageDiv = document.createElement('div');
    messageDiv.className='message bot';
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.appendChild(inputs);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function submitVisitors() {
    const adults = parseInt(document.getElementById('adults-input').value) || 0;
    const children = parseInt(document.getElementById('children-input').value) || 0;
    
    const totalVisitors = adults + children;
    if (totalVisitors <= 0) {
        addMessage('Please enter at least 1 visitor (adult or child)', 'bot');
        return;
    }

    if (children < 0) {
        addMessage('Number of children cannot be negative', 'bot');
        return;
    }

    if (adults < 0) {
        addMessage('Number of adults cannot be negative', 'bot');
        return;
    }
    
    // Store the validated numbers in currentBooking
    currentBooking.adults = adults;
    currentBooking.children = children;
    
    try {
        // Fetch current pricing
        const response = await fetch(`${BACKEND_URL}/api/pricing?nationality=${currentBooking.nationality}&ticketType=${currentBooking.ticketType}&date=${currentBooking.date}`);
        if (!response.ok) throw new Error('Failed to fetch pricing');
        const pricing = await response.json();
        
        // Calculate total amount with validated numbers
        currentBooking.adultPrice = pricing.adult_price;
        currentBooking.childPrice = pricing.child_price;
        currentBooking.amount = (adults * pricing.adult_price) + (children * pricing.child_price);
    } catch (error) {
        console.error('Error calculating total:', error);
        addMessage('Sorry, there was an error calculating the price. Please try again.', 'bot');
        return;
    }
    
    // Remove the visitor inputs
    const visitorInputs = document.querySelector('.visitor-inputs');
    if (visitorInputs) {
        visitorInputs.remove();
    }
    
    addMessage(`Selected visitors: ${adults} adults, ${children} children`, 'user');
    addMessage('Please enter your email address for booking confirmation:', 'bot');
    showEmailInput();
}

function showEmailInput() {
    const emailInput = document.createElement('div');
    emailInput.className = 'email-input-container';
    emailInput.innerHTML = `
        <input type="email" id="visitor-email" class="form-control" placeholder="Enter your email">
        <button onclick="submitEmail()" class="btn btn-primary mt-2">Submit</button>
    `;
    messagesContainer.appendChild(emailInput);
    document.getElementById('visitor-email').focus();
}

function submitEmail() {
    const emailInput = document.getElementById('visitor-email');
    const email = emailInput.value.trim();
    
    if (!email || !email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
        addMessage('Please enter a valid email address.', 'bot');
        return;
    }
    
    currentBooking.email = email;
    addMessage(`Email: ${email}`, 'user');
    
    // Remove email input
    const emailContainer = document.querySelector('.email-input-container');
    if (emailContainer) {
        emailContainer.remove();
    }
    
    // Show booking summary and payment options
    addMessage('Great! Here\'s your booking summary:', 'bot');
    updateBookingSummary();
    addMessage('Please review your booking details and proceed to payment.', 'bot');
    paymentSection.classList.remove('d-none');
}

function showTicketTypes() {
    const ticketTypes = ['Regular'];  // Updated to match backend
    const quickReplies = document.createElement('div');
    quickReplies.className = 'quick-replies';
    
    ticketTypes.forEach(type => {
        const button = document.createElement('button');
        button.className = 'quick-reply-btn';
        button.innerHTML = `<i class="bi bi-ticket-perforated"></i> ${type}`;
        button.onclick = () => selectTicketType(type);
        quickReplies.appendChild(button);
    });
    
    messagesContainer.appendChild(quickReplies);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function selectTicketType(ticketType) {
    currentBooking.ticketType = ticketType;
    
    // Remove ticket type options
    const quickReplies = document.querySelector('.quick-replies');
    if (quickReplies) {
        quickReplies.remove();
    }
    
    addMessage(`Selected ticket type: ${ticketType}`, 'user');
    addMessage('Please select your preferred time slot:', 'bot');
    showTimeSlots();
}

function showTimeSlots() {
    const timeSlots = ['10:00 AM', '2:00 PM'];
    const quickReplies = document.createElement('div');
    quickReplies.className = 'quick-replies';
    
    // Get current time
    const now = new Date();
    const currentHour = now.getHours();
    const currentMinutes = now.getMinutes();
    
    // Check if the selected date is today
    const selectedDate = new Date(currentBooking.date);
    const today = new Date();
    const isToday = selectedDate.toDateString() === today.toDateString();
    
    timeSlots.forEach(slot => {
        const [time, period] = slot.split(' ');
        const [hours, minutes] = time.split(':');
        let slotHour = parseInt(hours);
        if (period === 'PM' && slotHour !== 12) slotHour += 12;
        
        // Disable past time slots for today
        const isDisabled = isToday && (slotHour < currentHour || (slotHour === currentHour && parseInt(minutes) <= currentMinutes));
        
        const button = document.createElement('button');
        button.className = 'quick-reply-btn';
        if (isDisabled) {
            button.classList.add('disabled');
            button.disabled = true;
        }
        button.innerHTML = `<i class="bi bi-clock"></i> ${slot}${isDisabled ? ' (Past)' : ''}`;
        button.onclick = isDisabled ? null : () => selectTimeSlot(slot);
        quickReplies.appendChild(button);
    });
    
    messagesContainer.appendChild(quickReplies);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Add CSS for disabled buttons
const style = document.createElement('style');
style.textContent = `
    .quick-reply-btn.disabled {
        opacity: 0.5;
        cursor: not-allowed;
        background-color: #e9ecef;
    }
`;
document.head.appendChild(style);

function selectTimeSlot(timeSlot) {
    const quickReplies = document.querySelector('.quick-replies');
    if (quickReplies) {
        quickReplies.remove();
    }
    
    currentBooking.timeSlot = timeSlot;
    addMessage(`Selected time slot: ${timeSlot}`, 'user');
    addMessage('Please enter the number of visitors:', 'bot');
    showVisitorInputs();
}

// Payment handling
proceedPaymentBtn.addEventListener('click', async () => {
    try {
        proceedPaymentBtn.disabled = true;
        proceedPaymentBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Processing...';

        // Validate booking data
        const requiredFields = ['date', 'nationality', 'adults', 'ticketType', 'timeSlot', 'email'];
        const missingFields = requiredFields.filter(field => !currentBooking[field]);
        
        if (missingFields.length > 0) {
            throw new Error(`Missing required fields: ${missingFields.join(', ')}`);
        }

        // Create booking data object with proper type conversion
        const bookingData = {
            date: currentBooking.date,
            nationality: currentBooking.nationality,
            adults: parseInt(currentBooking.adults) || 0,
            children: parseInt(currentBooking.children) || 0,
            ticketType: currentBooking.ticketType,
            timeSlot: currentBooking.timeSlot,
            email: currentBooking.email,
            amount: parseFloat(currentBooking.amount) || 0
        };

        // Validate numeric fields
        if (typeof bookingData.children !== 'number' || bookingData.children < 0) {
            throw new Error('Invalid number of children');
        }
        if (typeof bookingData.adults !== 'number' || bookingData.adults <= 0) {
            throw new Error('Invalid number of adults');
        }

        // Log the prepared booking data
        console.log('Prepared booking data:', bookingData);

        const response = await createBooking(bookingData);
        console.log('Create booking response:', response);
        
        if (response.success) {
            // Display the confirmed booking details
            displayConfirmedBooking({
                id: response.booking_id,
                date: bookingData.date,
                adults: bookingData.adults,
                children: bookingData.children,
                amount: response.amount,
                email: bookingData.email
            });
        } else {
            throw new Error(response.message || 'Failed to create booking');
        }
    } catch (error) {
        console.error('Payment processing error:', error);
        addMessage(error.message || 'Failed to process payment. Please try again.', 'bot');
    } finally {
        proceedPaymentBtn.disabled = false;
        proceedPaymentBtn.innerHTML = '<i class="bi bi-credit-card"></i> Proceed to Payment';
    }
});

function displayConfirmedBooking(booking) {
    if (!booking || !booking.id) {
        console.error('Invalid booking data:', booking);
        return;
    }

    try {
        // Hide booking details and payment section
        bookingDetails.classList.add('d-none');
        paymentSection.classList.add('d-none');

        // Debug log to check the booking data
        console.log('Raw booking data:', booking);
        console.log('Date value:', booking.date);
        console.log('Adults value:', booking.adults);
        console.log('Children value:', booking.children);

        // Format the date with error handling
        let formattedDate = 'Date not available';
        if (booking.date) {
            try {
                formattedDate = new Date(booking.date).toLocaleDateString('en-US', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                });
            } catch (dateError) {
                console.error('Error formatting date:', dateError);
            }
        }

        // Ensure numeric values for adults and children
        const adults = parseInt(booking.adults) || 0;
        const children = parseInt(booking.children) || 0;

        // Show confirmed booking details
        confirmedBookingDetails.classList.remove('d-none');
        confirmedBookingId.textContent = booking.id;
        confirmedBookingDate.textContent = formattedDate;
        confirmedBookingVisitors.textContent = `${adults} Adults, ${children} Children`;
        confirmedBookingAmount.textContent = `₹${parseFloat(booking.amount || 0).toFixed(2)}`;

        // Add confirmation message with email
        addMessage(`Booking confirmed! Your booking ID is: ${booking.id}. A confirmation email has been sent to ${booking.email}`, 'bot');
        
        // Log the final displayed values for debugging
        console.log('Displayed values:', {
            id: booking.id,
            date: formattedDate,
            visitors: `${adults} Adults, ${children} Children`,
            amount: `₹${parseFloat(booking.amount || 0).toFixed(2)}`
        });
    } catch (error) {
        console.error('Error displaying confirmed booking:', error);
        addMessage('There was an error displaying your booking details. Please check your booking status using your booking ID.', 'bot');
    }
}

function updateBookingSummary() {
    if (currentBooking.date) {
        // Format the date properly
        const formattedDate = new Date(currentBooking.date).toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        
        // Update the DOM elements with proper checks
        if (bookingDate) {
            bookingDate.textContent = `Date: ${formattedDate}`;
        }
        if (bookingVisitors) {
            bookingVisitors.textContent = 
                `Visitors: ${currentBooking.adults || 0} adults, ${currentBooking.children || 0} children`;
        }
        // Calculate total using stored prices with null checks
        const adultPrice = currentBooking.adultPrice || 0;
        const childPrice = currentBooking.childPrice || 0;
        const total = (currentBooking.adults * adultPrice) + 
                     (currentBooking.children * childPrice);
        const formattedAmount = parseFloat(total).toFixed(2);
        
        if (bookingAmount) {
            bookingAmount.textContent = `Total: ₹${formattedAmount}`;
        }
        
        // Show/hide sections with proper checks
        if (bookingDetails) {
            bookingDetails.classList.remove('d-none');
        }
        if (paymentSection && total > 0) {
            paymentSection.classList.remove('d-none');
        }
        
        // Log for debugging
        console.log('Current Booking:', currentBooking);
    }
}

// Booking status checker
async function showBookingStatus() {
    addMessage('Please enter your booking ID:', 'bot');
    
    // Create and show input form
    const inputForm = document.createElement('form');
    inputForm.className = 'booking-id-form';
    inputForm.innerHTML = `
        <div class="input-group mb-3">
            <input type="text" class="form-control" id="bookingIdInput" placeholder="Enter Booking ID" required>
            <button class="btn btn-primary" type="submit">Check Status</button>
        </div>
    `;
    
    inputForm.onsubmit = async (e) => {
        e.preventDefault();
        const bookingId = document.getElementById('bookingIdInput').value.trim();
        
        if (!bookingId) {
            addMessage('Please enter a valid booking ID.', 'bot');
            return;
        }
        
        try {
            const response = await fetch(`${BACKEND_URL}/api/bookings/${bookingId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                credentials: 'include',
                mode: 'cors'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.status === 'success' && data.data) {
                displayBooking({
                    id: data.data.id,
                    date: data.data.date,
                    time_slot: data.data.time_slot,
                    adult_count: data.data.adult_count,
                    child_count: data.data.child_count,
                    total_amount: data.data.total_amount,
                    status: data.data.status,
                    payment_status: data.data.payment_status
                });
            } else {
                throw new Error(data.message || 'Invalid response format');
            }
        } catch (error) {
            console.error('Error fetching booking:', error);
            addMessage('Sorry, we couldn\'t find a booking with that ID. Please check and try again.', 'bot');
        }
    };
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user';
    messageDiv.appendChild(inputForm);
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Focus on the input
    document.getElementById('bookingIdInput').focus();
}

// Display a single booking
function displayBooking(booking) {
    const formattedDate = new Date(booking.date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });

    // Create DOM elements instead of using template string
    const resultDiv = document.createElement('div');
    resultDiv.className = 'booking-result';

    // Status tag for booking status
    const statusDiv = document.createElement('div');
    statusDiv.className = `booking-status-tag ${booking.status.toLowerCase()}`;
    statusDiv.textContent = booking.status;
    resultDiv.appendChild(statusDiv);

    // Status tag for payment status
    const paymentStatusDiv = document.createElement('div');
    paymentStatusDiv.className = `booking-status-tag payment-${booking.payment_status.toLowerCase()}`;
    paymentStatusDiv.textContent = `Payment: ${booking.payment_status}`;
    resultDiv.appendChild(paymentStatusDiv);

    const infoDiv = document.createElement('div');
    infoDiv.className = 'booking-info';

    const timeDiv = document.createElement('div');
    timeDiv.className = 'booking-time';
    timeDiv.textContent = `${formattedDate} at ${booking.time_slot}`;
    infoDiv.appendChild(timeDiv);

    const visitorsDiv = document.createElement('div');
    visitorsDiv.className = 'booking-visitors';
    const totalVisitors = booking.adult_count + booking.child_count;
    const visitorText = [];
    if (booking.adult_count > 0) visitorText.push(`${booking.adult_count} Adult${booking.adult_count > 1 ? 's' : ''}`);
    if (booking.child_count > 0) visitorText.push(`${booking.child_count} Child${booking.child_count > 1 ? 'ren' : ''}`);
    visitorsDiv.textContent = visitorText.join(', ');
    infoDiv.appendChild(visitorsDiv);

    const amountDiv = document.createElement('div');
    amountDiv.className = 'booking-amount';
    amountDiv.textContent = `₹${booking.total_amount.toFixed(2)}`;
    infoDiv.appendChild(amountDiv);

    resultDiv.appendChild(infoDiv);

    const referenceDiv = document.createElement('div');
    referenceDiv.className = 'booking-reference';
    referenceDiv.textContent = `Reference: ${booking.id}`;
    resultDiv.appendChild(referenceDiv);

    // Create message container
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot';
    messageDiv.appendChild(resultDiv);
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Add the necessary CSS if not already present
    if (!document.getElementById('booking-styles')) {
        const styles = document.createElement('style');
        styles.id = 'booking-styles';
        styles.textContent = `
            .booking-result {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 16px;
                max-width: 400px;
            }
            .booking-status-tag {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 0.9em;
                font-weight: 500;
                margin: 0 8px 12px 0;
            }
            .booking-status-tag.confirmed {
                background: #e3f2fd;
                color: #1976d2;
            }
            .booking-status-tag.pending {
                background: #fff3e0;
                color: #f57c00;
            }
            .booking-status-tag.cancelled {
                background: #ffebee;
                color: #d32f2f;
            }
            .booking-status-tag.payment-pending {
                background: #fff3e0;
                color: #f57c00;
            }
            .booking-status-tag.payment-completed {
                background: #e8f5e9;
                color: #2e7d32;
            }
            .booking-status-tag.payment-failed {
                background: #ffebee;
                color: #d32f2f;
            }
            .booking-info {
                margin: 12px 0;
            }
            .booking-time {
                font-size: 1.1em;
                font-weight: 500;
                margin-bottom: 8px;
            }
            .booking-visitors, .booking-amount {
                color: #666;
                font-size: 0.95em;
                margin: 4px 0;
            }
            .booking-reference {
                font-size: 0.85em;
                color: #888;
                margin-top: 12px;
            }
        `;
        document.head.appendChild(styles);
    }
}

// Fetch calendar data
async function fetchCalendarData(year, month) {
    try {
        // Show loading state
        document.querySelectorAll('.calendar td[data-date]').forEach(cell => {
            cell.classList.add('loading');
            const slotsDiv = cell.querySelector('.slots');
            if (slotsDiv) {
                slotsDiv.textContent = 'Loading...';
            }
        });

        const response = await fetch(`${BACKEND_URL}/api/calendar/monthly/${year}/${month}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Calendar data received:', data); // Debug log
        renderCalendar(data);

    } catch (error) {
        console.error('Error fetching calendar data:', error);
        // Show error state
        document.querySelectorAll('.calendar td[data-date]').forEach(cell => {
            cell.classList.remove('loading');
            cell.classList.add('error');
            const slotsDiv = cell.querySelector('.slots');
            if (slotsDiv) {
                slotsDiv.textContent = 'Error loading';
            }
        });
    }
}

// Render calendar
function renderCalendar(data) {
    const calendar = document.getElementById('calendar');
    if (!calendar) return;
    
    Object.entries(data).forEach(([date, info]) => {
        const cell = calendar.querySelector(`td[data-date="${date}"]`);
        if (!cell) return;

        // Remove any existing classes
        cell.classList.remove('available', 'limited', 'full', 'unavailable', 'loading', 'error');
        
        const slotsDiv = cell.querySelector('.slots');
        if (!slotsDiv) return;

        // Calculate total availability
        if (info.slots && info.slots.length > 0) {
            const totalAvailable = info.slots.reduce((sum, slot) => sum + slot.available, 0);
            const totalCapacity = info.slots.reduce((sum, slot) => sum + slot.capacity, 0);
            
            // Check if all slots for the day are in the past
            const now = new Date();
            const cellDate = new Date(date);
            const isToday = cellDate.toDateString() === now.toDateString();
            const currentHour = now.getHours();
            
            let allSlotsInPast = false;
            if (isToday) {
                allSlotsInPast = info.slots.every(slot => {
                    const [time, period] = slot.time.split(' ');
                    const [hours] = time.split(':');
                    let slotHour = parseInt(hours);
                    if (period === 'PM' && slotHour !== 12) slotHour += 12;
                    return slotHour <= currentHour;
                });
            }
            
            // Determine status and apply appropriate class
            if (totalCapacity === 0 || allSlotsInPast) {
                cell.classList.add('unavailable');
                slotsDiv.textContent = 'No slots';
            } else if (totalAvailable === 0) {
                cell.classList.add('full');
                slotsDiv.textContent = 'Full';
                // Make the cell appear greyed out when full
                cell.style.opacity = '0.5';
                cell.style.backgroundColor = '#e9ecef';
            } else if (totalAvailable <= 10) {
                cell.classList.add('limited');
                slotsDiv.textContent = `${totalAvailable} slots left`;
            } else {
                cell.classList.add('available');
                slotsDiv.textContent = `${totalAvailable} slots`;
            }

            // Create detailed tooltip
            const tooltipContent = info.slots
                .map(slot => {
                    if (isToday) {
                        const [time, period] = slot.time.split(' ');
                        const [hours] = time.split(':');
                        let slotHour = parseInt(hours);
                        if (period === 'PM' && slotHour !== 12) slotHour += 12;
                        if (slotHour <= currentHour) {
                            return `${slot.time}: Past`;
                        }
                    }
                    return `${slot.time}: ${slot.available}/${slot.capacity} available`;
                })
                .join('\n');
            cell.setAttribute('title', tooltipContent);

        } else {
            cell.classList.add('unavailable');
            slotsDiv.textContent = 'No slots';
        }
    });
}

// Add CSS for calendar cells
const calendarStyle = document.createElement('style');
calendarStyle.textContent = `
    td.full {
        opacity: 0.5;
        background-color: #e9ecef !important;
        cursor: not-allowed;
    }
    td.full:hover {
        background-color: #e9ecef !important;
    }
`;
document.head.appendChild(calendarStyle);

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    messagesContainer.appendChild(errorDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function createBooking(bookingData) {
    try {
        console.log('=== Starting createBooking ===');
        console.log('Backend URL:', BACKEND_URL);
        console.log('Gateway URL:', GATEWAY_URL);
        console.log('Original booking data:', bookingData);

        // Ensure all numeric fields are properly parsed as integers
        const processedBookingData = {
            date: bookingData.date,
            nationality: bookingData.nationality,
            adults: parseInt(bookingData.adults) || 0,
            children: parseInt(bookingData.children || 0),
            ticketType: bookingData.ticketType,
            timeSlot: bookingData.timeSlot,
            email: bookingData.email,
            amount: parseFloat(bookingData.amount) || 0
        };

        console.log('Processed booking data:', processedBookingData);
        console.log('Attempting to send request to:', `${BACKEND_URL}/api/bookings/create`);

        const response = await fetch(`${BACKEND_URL}/api/bookings/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include',
            mode: 'cors',
            body: JSON.stringify(processedBookingData)
        });

        console.log('Response status:', response.status);
        console.log('Response headers:', Object.fromEntries(response.headers.entries()));

        const data = await response.json();
        console.log('Response data:', data);
        
        if (!response.ok) {
            console.error('Booking creation failed:', data.error);
            addMessage(`Booking failed: ${data.error}`, 'bot');
            throw new Error(data.error || 'Failed to create booking');
        }

        // Send confirmation email
        console.log('Sending confirmation email...');
        const emailData = {
            to_email: processedBookingData.email,
            booking_id: data.booking_id,
            booking_details: {
                date: processedBookingData.date,
                timeSlot: processedBookingData.timeSlot,
                adults: processedBookingData.adults,
                children: processedBookingData.children,
                amount: data.amount || processedBookingData.amount
            }
        };

        console.log('Email request data:', emailData);
        const emailResponse = await fetch(`${GATEWAY_URL}/api/email/send`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'include',
            mode: 'cors',
            body: JSON.stringify(emailData)
        });

        console.log('Email response status:', emailResponse.status);
        if (!emailResponse.ok) {
            const errorText = await emailResponse.text();
            console.warn('Email sending failed:', errorText);
            // Don't fail the booking if email fails
            data.email_status = 'failed';
        } else {
            const emailResult = await emailResponse.json();
            console.log('Email response:', emailResult);
            data.email_status = 'sent';
        }

        return data;
    } catch (error) {
        console.error('Booking creation error:', error);
        throw error;
    }
}
