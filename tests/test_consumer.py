import pytest
import asyncio
import json
import os
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from azure.servicebus import ServiceBusMessage
from azure.servicebus.exceptions import ServiceBusError
import signal

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from consumer import (
    validate_environment_variables,
    setup_signal_handlers,
    safe_abandon_message,
    safe_complete_message,
    process_message_async,
    cleanup_completed_tasks,
    wait_for_available_slot,
    graceful_shutdown_tasks,
    run_service_bus_processor_async,
    run_service_bus_processor,
    shutdown_event
)

# Enable async testing
pytest_plugins = ('pytest_asyncio',)


class TestEnvironmentValidation:
    """Test suite for environment variable validation."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Store original environment
        self.original_env = os.environ.copy()
        # Clear relevant environment variables
        env_vars_to_clear = [
            'SERVICE_BUS_CONNECTION_STR',
            'SERVICE_BUS_QUEUE_NAME',
            'AI_MODEL_NAME',
            'AI_API_KEY',
            'AI_ENDPOINT',
            'API_VERSION'
        ]
        for var in env_vars_to_clear:
            if var in os.environ:
                del os.environ[var]

    def teardown_method(self):
        """Clean up after each test method."""
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_validate_environment_variables_success(self):
        """Test successful validation when all required environment variables are present."""
        # Setup
        required_env_vars = {
            'SERVICE_BUS_CONNECTION_STR': 'fake_connection_string',
            'SERVICE_BUS_QUEUE_NAME': 'test_queue',
            'AI_MODEL_NAME': 'gpt-4o',
            'AI_API_KEY': 'fake_api_key',
            'AI_ENDPOINT': 'https://fake.endpoint.com',
            'API_VERSION': '2024-02-01'
        }
        
        for key, value in required_env_vars.items():
            os.environ[key] = value

        # Execute
        result = validate_environment_variables()

        # Verify
        assert result == required_env_vars

    def test_validate_environment_variables_missing_single_var(self):
        """Test validation failure when a single required variable is missing."""
        # Setup - missing AI_API_KEY
        os.environ['SERVICE_BUS_CONNECTION_STR'] = 'fake_connection_string'
        os.environ['SERVICE_BUS_QUEUE_NAME'] = 'test_queue'
        os.environ['AI_MODEL_NAME'] = 'gpt-4o'
        os.environ['AI_ENDPOINT'] = 'https://fake.endpoint.com'
        os.environ['API_VERSION'] = '2024-02-01'

        # Execute & Verify
        with pytest.raises(ValueError, match="Missing required environment variables: AI_API_KEY"):
            validate_environment_variables()

    def test_validate_environment_variables_missing_multiple_vars(self):
        """Test validation failure when multiple required variables are missing."""
        # Setup - only set a couple of variables
        os.environ['SERVICE_BUS_CONNECTION_STR'] = 'fake_connection_string'
        os.environ['AI_MODEL_NAME'] = 'gpt-4o'

        # Execute & Verify
        with pytest.raises(ValueError, match="Missing required environment variables"):
            validate_environment_variables()

    def test_validate_environment_variables_empty_values(self):
        """Test validation failure when environment variables have empty values."""
        # Setup - set empty values
        required_env_vars = {
            'SERVICE_BUS_CONNECTION_STR': '',
            'SERVICE_BUS_QUEUE_NAME': 'test_queue',
            'AI_MODEL_NAME': 'gpt-4o',
            'AI_API_KEY': '',
            'AI_ENDPOINT': 'https://fake.endpoint.com',
            'API_VERSION': '2024-02-01'
        }
        
        for key, value in required_env_vars.items():
            os.environ[key] = value

        # Execute & Verify
        with pytest.raises(ValueError, match="Missing required environment variables"):
            validate_environment_variables()


class TestSignalHandlers:
    """Test suite for signal handler setup."""

    def test_setup_signal_handlers(self):
        """Test that signal handlers are properly configured."""
        # Execute
        setup_signal_handlers()

        # Verify that signal handlers are set (this is a basic test)
        # In a real scenario, testing signal handling is complex and may require more sophisticated approaches
        assert signal.signal(signal.SIGTERM, signal.SIG_DFL) != signal.SIG_DFL
        assert signal.signal(signal.SIGINT, signal.SIG_DFL) != signal.SIG_DFL
        
        # Restore default handlers
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)


class TestMessageHandling:
    """Test suite for Service Bus message handling functions."""

    @pytest.mark.asyncio
    async def test_safe_abandon_message_success(self):
        """Test successful message abandonment."""
        # Setup
        mock_receiver = AsyncMock()
        mock_message = Mock()
        mock_receiver.abandon_message.return_value = None

        # Execute
        await safe_abandon_message(mock_receiver, mock_message)

        # Verify
        mock_receiver.abandon_message.assert_called_once_with(mock_message)

    @pytest.mark.asyncio
    async def test_safe_abandon_message_failure(self):
        """Test message abandonment handles exceptions gracefully."""
        # Setup
        mock_receiver = AsyncMock()
        mock_message = Mock()
        mock_receiver.abandon_message.side_effect = ServiceBusError("Abandon failed")

        # Execute (should not raise exception)
        await safe_abandon_message(mock_receiver, mock_message)

        # Verify
        mock_receiver.abandon_message.assert_called_once_with(mock_message)

    @pytest.mark.asyncio
    async def test_safe_complete_message_success(self):
        """Test successful message completion."""
        # Setup
        mock_receiver = AsyncMock()
        mock_message = Mock()
        mock_receiver.complete_message.return_value = None

        # Execute
        await safe_complete_message(mock_receiver, mock_message)

        # Verify
        mock_receiver.complete_message.assert_called_once_with(mock_message)

    @pytest.mark.asyncio
    async def test_safe_complete_message_failure_calls_abandon(self):
        """Test that failed message completion calls abandon."""
        # Setup
        mock_receiver = AsyncMock()
        mock_message = Mock()
        mock_receiver.complete_message.side_effect = ServiceBusError("Complete failed")
        mock_receiver.abandon_message.return_value = None

        # Execute
        await safe_complete_message(mock_receiver, mock_message)

        # Verify
        mock_receiver.complete_message.assert_called_once_with(mock_message)
        mock_receiver.abandon_message.assert_called_once_with(mock_message)


class TestMessageProcessing:
    """Test suite for message processing functionality."""

    @pytest.mark.asyncio
    @patch('consumer.PromptProcessor')
    async def test_process_message_async_success(self, mock_prompt_processor_class):
        """Test successful message processing."""
        # Setup
        mock_receiver = AsyncMock()
        mock_message = Mock()
        mock_prompt_processor = AsyncMock()
        mock_prompt_processor_class.return_value.__aenter__.return_value = mock_prompt_processor
        
        # Create valid JSON message
        test_payload = {
            "skills_list": ["writing", "grammar"],
            "essay": "This is a test essay."
        }
        message_body = json.dumps(test_payload).encode('utf-8')
        mock_message.body = [message_body]
        
        mock_prompt_processor.process_payload.return_value = "Evaluation complete"
        mock_receiver.complete_message.return_value = None

        # Execute
        await process_message_async(
            mock_message, mock_receiver, 
            "gpt-4o", "fake_key", "https://fake.endpoint.com", "2024-02-01"
        )

        # Verify
        mock_prompt_processor.process_payload.assert_called_once_with(test_payload)
        mock_receiver.complete_message.assert_called_once_with(mock_message)

    @pytest.mark.asyncio
    async def test_process_message_async_invalid_json(self):
        """Test processing of message with invalid JSON."""
        # Setup
        mock_receiver = AsyncMock()
        mock_message = Mock()
        mock_message.body = [b"invalid json content"]
        mock_receiver.abandon_message.return_value = None

        # Execute
        await process_message_async(
            mock_message, mock_receiver,
            "gpt-4o", "fake_key", "https://fake.endpoint.com", "2024-02-01"
        )

        # Verify
        mock_receiver.abandon_message.assert_called_once_with(mock_message)

    @pytest.mark.asyncio
    @patch('consumer.PromptProcessor')
    async def test_process_message_async_processing_error(self, mock_prompt_processor_class):
        """Test message processing handles processing errors."""
        # Setup
        mock_receiver = AsyncMock()
        mock_message = Mock()
        mock_prompt_processor = AsyncMock()
        mock_prompt_processor_class.return_value.__aenter__.return_value = mock_prompt_processor
        
        test_payload = {"skills_list": [], "essay": "Test"}
        message_body = json.dumps(test_payload).encode('utf-8')
        mock_message.body = [message_body]
        
        mock_prompt_processor.process_payload.side_effect = Exception("Processing failed")
        mock_receiver.abandon_message.return_value = None

        # Execute
        await process_message_async(
            mock_message, mock_receiver,
            "gpt-4o", "fake_key", "https://fake.endpoint.com", "2024-02-01"
        )

        # Verify
        mock_receiver.abandon_message.assert_called_once_with(mock_message)


class TestTaskManagement:
    """Test suite for task management functions."""

    @pytest.mark.asyncio
    async def test_cleanup_completed_tasks_empty_set(self):
        """Test cleanup with empty task set."""
        # Execute
        result = await cleanup_completed_tasks(set())
        
        # Verify
        assert result == set()

    @pytest.mark.asyncio
    async def test_cleanup_completed_tasks_no_completed(self):
        """Test cleanup when no tasks are completed."""
        # Setup
        task1 = asyncio.create_task(asyncio.sleep(1))
        task2 = asyncio.create_task(asyncio.sleep(1))
        tasks = {task1, task2}

        try:
            # Execute
            result = await cleanup_completed_tasks(tasks)
            
            # Verify
            assert result == tasks
        finally:
            # Cleanup
            task1.cancel()
            task2.cancel()
            try:
                await task1
            except asyncio.CancelledError:
                pass
            try:
                await task2
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_cleanup_completed_tasks_with_completed(self):
        """Test cleanup removes completed tasks."""
        # Setup
        async def quick_task():
            return "completed"
        
        task1 = asyncio.create_task(quick_task())
        task2 = asyncio.create_task(asyncio.sleep(1))
        tasks = {task1, task2}
        
        # Wait for first task to complete
        await asyncio.sleep(0.1)

        try:
            # Execute
            result = await cleanup_completed_tasks(tasks)
            
            # Verify
            assert task1 not in result
            assert task2 in result or len(result) == 0  # task2 might also complete quickly
        finally:
            # Cleanup
            task2.cancel()
            try:
                await task2
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_wait_for_available_slot_under_limit(self):
        """Test wait_for_available_slot when under concurrency limit."""
        # Setup
        task1 = asyncio.create_task(asyncio.sleep(1))
        tasks = {task1}

        try:
            # Execute
            result = await wait_for_available_slot(tasks, max_concurrent_tasks=5)
            
            # Verify
            assert result == tasks
        finally:
            # Cleanup
            task1.cancel()
            try:
                await task1
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_wait_for_available_slot_at_limit(self):
        """Test wait_for_available_slot when at concurrency limit."""
        # Setup
        async def quick_task():
            await asyncio.sleep(0.1)
            return "completed"
        
        task1 = asyncio.create_task(quick_task())
        task2 = asyncio.create_task(asyncio.sleep(1))
        tasks = {task1, task2}

        try:
            # Execute
            result = await wait_for_available_slot(tasks, max_concurrent_tasks=2)
            
            # Verify that at least one task completed
            assert len(result) < len(tasks)
        finally:
            # Cleanup
            for task in tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

    @pytest.mark.asyncio
    async def test_graceful_shutdown_tasks_empty_set(self):
        """Test graceful shutdown with empty task set."""
        # Execute
        result = await graceful_shutdown_tasks(set(), timeout=1)
        
        # Verify
        assert result is True

    @pytest.mark.asyncio
    async def test_graceful_shutdown_tasks_successful(self):
        """Test graceful shutdown when all tasks complete in time."""
        # Setup
        async def quick_task():
            await asyncio.sleep(0.1)
            return "completed"
        
        task1 = asyncio.create_task(quick_task())
        task2 = asyncio.create_task(quick_task())
        tasks = {task1, task2}

        # Execute
        result = await graceful_shutdown_tasks(tasks, timeout=1)
        
        # Verify
        assert result is True

    @pytest.mark.asyncio
    async def test_graceful_shutdown_tasks_timeout(self):
        """Test graceful shutdown when tasks timeout."""
        # Setup
        task1 = asyncio.create_task(asyncio.sleep(2))  # Will timeout
        tasks = {task1}

        # Execute
        result = await graceful_shutdown_tasks(tasks, timeout=0.1)
        
        # Verify
        assert result is False
        assert task1.cancelled()


class TestServiceBusProcessor:
    """Test suite for the main Service Bus processor."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Clear shutdown event
        shutdown_event.clear()
        
        # Store original environment
        self.original_env = os.environ.copy()
        
        # Set required environment variables
        os.environ.update({
            'SERVICE_BUS_CONNECTION_STR': 'fake_connection_string',
            'SERVICE_BUS_QUEUE_NAME': 'test_queue',
            'AI_MODEL_NAME': 'gpt-4o',
            'AI_API_KEY': 'fake_api_key',
            'AI_ENDPOINT': 'https://fake.endpoint.com',
            'API_VERSION': '2024-02-01'
        })

    def teardown_method(self):
        """Clean up after each test method."""
        # Clear shutdown event
        shutdown_event.clear()
        
        # Restore original environment
        os.environ.clear()
        os.environ.update(self.original_env)

    @pytest.mark.asyncio
    @patch('consumer.AsyncServiceBusClient')
    async def test_run_service_bus_processor_async_immediate_shutdown(self, mock_service_bus_client):
        """Test processor handles immediate shutdown signal."""
        # Setup
        shutdown_event.set()  # Signal shutdown immediately
        
        mock_client = AsyncMock()
        mock_service_bus_client.from_connection_string.return_value.__aenter__.return_value = mock_client

        # Execute
        await run_service_bus_processor_async()
        
        # Verify that the client was created but receiver was not called extensively
        mock_service_bus_client.from_connection_string.assert_called_once()

    @pytest.mark.asyncio
    @patch('consumer.AsyncServiceBusClient')
    @patch('consumer.process_message_async')
    async def test_run_service_bus_processor_async_message_processing(self, mock_process_message, mock_service_bus_client):
        """Test processor handles message processing correctly."""
        # Setup
        mock_client = AsyncMock()
        mock_receiver = AsyncMock()
        mock_service_bus_client.from_connection_string.return_value.__aenter__.return_value = mock_client
        mock_client.get_queue_receiver.return_value.__aenter__.return_value = mock_receiver
        
        # Create a mock message
        mock_message = Mock()
        mock_receiver.receive_messages.side_effect = [
            [mock_message],  # First call returns one message
            []  # Second call returns no messages, triggering shutdown
        ]
        
        # Setup async mock for message processing
        mock_process_message.return_value = None
        
        # Set shutdown after first iteration
        async def side_effect(*args):
            shutdown_event.set()
            
        mock_process_message.side_effect = side_effect

        # Execute
        await run_service_bus_processor_async()
        
        # Verify
        mock_receiver.receive_messages.assert_called()
        mock_process_message.assert_called_once()

    def test_run_service_bus_processor_missing_env_vars(self):
        """Test that processor raises error when environment variables are missing."""
        # Setup - clear environment variables
        for key in ['SERVICE_BUS_CONNECTION_STR', 'AI_API_KEY']:
            if key in os.environ:
                del os.environ[key]

        # Execute & Verify
        with pytest.raises(ValueError):
            run_service_bus_processor()

    @patch('consumer.setup_signal_handlers')
    @patch('consumer.asyncio.run')
    def test_run_service_bus_processor_signal_setup(self, mock_asyncio_run, mock_setup_signals):
        """Test that signal handlers are set up when running processor."""
        # Setup
        mock_asyncio_run.side_effect = KeyboardInterrupt()  # Simulate interrupt
        
        # Execute
        run_service_bus_processor()
        
        # Verify
        mock_setup_signals.assert_called_once()
        mock_asyncio_run.assert_called_once()


class TestIntegration:
    """Integration tests for the complete consumer functionality."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        shutdown_event.clear()
        self.original_env = os.environ.copy()
        
        # Set up complete environment
        os.environ.update({
            'SERVICE_BUS_CONNECTION_STR': 'fake_connection_string',
            'SERVICE_BUS_QUEUE_NAME': 'test_queue',
            'AI_MODEL_NAME': 'gpt-4o',
            'AI_API_KEY': 'fake_api_key',
            'AI_ENDPOINT': 'https://fake.endpoint.com',
            'API_VERSION': '2024-02-01'
        })

    def teardown_method(self):
        """Clean up after each test method."""
        shutdown_event.clear()
        os.environ.clear()
        os.environ.update(self.original_env)

    @pytest.mark.asyncio
    @patch('consumer.AsyncServiceBusClient')
    @patch('consumer.PromptProcessor')
    async def test_end_to_end_message_processing(self, mock_prompt_processor_class, mock_service_bus_client):
        """Test complete end-to-end message processing flow."""
        # Setup
        mock_client = AsyncMock()
        mock_receiver = AsyncMock()
        mock_prompt_processor = AsyncMock()
        
        mock_service_bus_client.from_connection_string.return_value.__aenter__.return_value = mock_client
        mock_client.get_queue_receiver.return_value.__aenter__.return_value = mock_receiver
        mock_prompt_processor_class.return_value.__aenter__.return_value = mock_prompt_processor
        
        # Create test message
        test_payload = {
            "skills_list": ["writing", "grammar"],
            "essay": "This is a test essay for evaluation."
        }
        mock_message = Mock()
        mock_message.body = [json.dumps(test_payload).encode('utf-8')]
        
        # Configure receiver to return message once then empty
        message_call_count = 0
        async def receive_messages_side_effect(*args, **kwargs):
            nonlocal message_call_count
            message_call_count += 1
            if message_call_count == 1:
                return [mock_message]
            else:
                shutdown_event.set()  # Trigger shutdown after first message
                return []
                
        mock_receiver.receive_messages.side_effect = receive_messages_side_effect
        mock_receiver.complete_message.return_value = None
        mock_prompt_processor.process_payload.return_value = "Essay evaluated successfully"

        # Execute
        await run_service_bus_processor_async()

        # Verify
        mock_prompt_processor.process_payload.assert_called_once_with(test_payload)
        mock_receiver.complete_message.assert_called_once_with(mock_message)


# Fixtures for reuse across tests
@pytest.fixture
def mock_service_bus_message():
    """Fixture providing a mock Service Bus message."""
    message = Mock(spec=ServiceBusMessage)
    test_payload = {
        "skills_list": ["writing", "grammar", "coherence"],
        "essay": "This is a test essay that needs to be evaluated for various skills."
    }
    message.body = [json.dumps(test_payload).encode('utf-8')]
    return message


@pytest.fixture
def mock_receiver():
    """Fixture providing a mock Service Bus receiver."""
    receiver = AsyncMock()
    receiver.complete_message.return_value = None
    receiver.abandon_message.return_value = None
    return receiver


@pytest.fixture
def test_environment():
    """Fixture providing test environment variables."""
    return {
        'SERVICE_BUS_CONNECTION_STR': 'Endpoint=sb://test.servicebus.windows.net/;SharedAccessKeyName=test;SharedAccessKey=fake',
        'SERVICE_BUS_QUEUE_NAME': 'essay-evaluation-queue',
        'AI_MODEL_NAME': 'gpt-4o',
        'AI_API_KEY': 'fake-api-key-12345',
        'AI_ENDPOINT': 'https://fake-ai-endpoint.openai.azure.com/',
        'API_VERSION': '2024-02-01-preview'
    }


# Parameterized tests for different error scenarios
@pytest.mark.parametrize("missing_env_var", [
    'SERVICE_BUS_CONNECTION_STR',
    'SERVICE_BUS_QUEUE_NAME', 
    'AI_MODEL_NAME',
    'AI_API_KEY',
    'AI_ENDPOINT',
    'API_VERSION'
])
def test_validate_environment_variables_missing_specific_var(missing_env_var):
    """Test that validation fails for each specific missing environment variable."""
    # Setup - set all variables except the one being tested
    all_vars = {
        'SERVICE_BUS_CONNECTION_STR': 'fake_connection_string',
        'SERVICE_BUS_QUEUE_NAME': 'test_queue',
        'AI_MODEL_NAME': 'gpt-4o',
        'AI_API_KEY': 'fake_api_key',
        'AI_ENDPOINT': 'https://fake.endpoint.com',
        'API_VERSION': '2024-02-01'
    }
    
    # Clear environment first
    for var in all_vars.keys():
        if var in os.environ:
            del os.environ[var]
    
    # Set all variables except the missing one
    for var, value in all_vars.items():
        if var != missing_env_var:
            os.environ[var] = value

    # Execute & Verify
    with pytest.raises(ValueError, match=f"Missing required environment variables: {missing_env_var}"):
        validate_environment_variables()

    # Cleanup
    for var in all_vars.keys():
        if var in os.environ:
            del os.environ[var]