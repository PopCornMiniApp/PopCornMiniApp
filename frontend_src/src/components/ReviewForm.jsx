import { useState } from 'react';
import { api } from '../utils/api';

/**
 * ReviewForm Component
 * Professional form for adding/editing reviews with 1-10 rating scale
 * Supports Dark/Light mode and Arabic/English languages
 */
const ReviewForm = ({ contentType, contentId, existingReview = null, onSuccess, onCancel }) => {
  const [rating, setRating] = useState(existingReview?.rating || 0);
  const [comment, setComment] = useState(existingReview?.comment || '');
  const [hoveredRating, setHoveredRating] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const isArabic = document.documentElement.dir === 'rtl';

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (rating < 1 || rating > 10) {
      setError(isArabic ? 'يرجى اختيار تقييم من 1 إلى 10' : 'Please select a rating from 1 to 10');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      if (existingReview) {
        // Update existing review
        await api.updateReview(existingReview.id, rating, comment || null);
      } else {
        // Add new review
        await api.addReview(contentType, contentId, rating, comment || null);
      }
      
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      console.error('Failed to submit review:', err);
      setError(
        isArabic 
          ? 'فشل في إرسال التقييم. يرجى المحاولة مرة أخرى.' 
          : 'Failed to submit review. Please try again.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderStars = () => {
    const stars = [];
    const displayRating = hoveredRating || rating;

    for (let i = 1; i <= 10; i++) {
      stars.push(
        <button
          key={i}
          type="button"
          className={`star-button ${i <= displayRating ? 'active' : ''}`}
          onMouseEnter={() => setHoveredRating(i)}
          onMouseLeave={() => setHoveredRating(0)}
          onClick={() => setRating(i)}
          disabled={isSubmitting}
        >
          <svg
            className="star-icon"
            fill={i <= displayRating ? 'currentColor' : 'none'}
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
            />
          </svg>
        </button>
      );
    }

    return stars;
  };

  const getRatingLabel = () => {
    if (rating === 0) return isArabic ? 'اختر تقييمك' : 'Select your rating';
    if (rating >= 9) return isArabic ? 'ممتاز' : 'Excellent';
    if (rating >= 7) return isArabic ? 'جيد جداً' : 'Very Good';
    if (rating >= 5) return isArabic ? 'جيد' : 'Good';
    if (rating >= 3) return isArabic ? 'مقبول' : 'Fair';
    return isArabic ? 'ضعيف' : 'Poor';
  };

  return (
    <div className="review-form-container">
      <form onSubmit={handleSubmit} className="review-form">
        <div className="form-header">
          <h3 className="form-title">
            {existingReview 
              ? (isArabic ? 'تعديل التقييم' : 'Edit Review')
              : (isArabic ? 'إضافة تقييم' : 'Add Review')
            }
          </h3>
        </div>

        {error && (
          <div className="error-message">
            <svg className="error-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        <div className="rating-section">
          <label className="rating-label">
            {isArabic ? 'التقييم (1-10)' : 'Rating (1-10)'}
          </label>
          <div className="stars-container">
            {renderStars()}
          </div>
          <div className="rating-display">
            <span className="rating-number">{rating}/10</span>
            <span className="rating-text">{getRatingLabel()}</span>
          </div>
        </div>

        <div className="comment-section">
          <label htmlFor="comment" className="comment-label">
            {isArabic ? 'التعليق (اختياري)' : 'Comment (Optional)'}
          </label>
          <textarea
            id="comment"
            className="comment-textarea"
            rows="4"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder={isArabic ? 'شارك رأيك حول هذا العمل...' : 'Share your thoughts about this content...'}
            disabled={isSubmitting}
            maxLength={500}
          />
          <div className="character-count">
            {comment.length}/500
          </div>
        </div>

        <div className="form-actions">
          {onCancel && (
            <button
              type="button"
              className="btn-cancel"
              onClick={onCancel}
              disabled={isSubmitting}
            >
              {isArabic ? 'إلغاء' : 'Cancel'}
            </button>
          )}
          <button
            type="submit"
            className="btn-submit"
            disabled={isSubmitting || rating === 0}
          >
            {isSubmitting ? (
              <>
                <svg className="spinner" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span>{isArabic ? 'جاري الإرسال...' : 'Submitting...'}</span>
              </>
            ) : (
              <span>{existingReview ? (isArabic ? 'تحديث' : 'Update') : (isArabic ? 'إرسال' : 'Submit')}</span>
            )}
          </button>
        </div>
      </form>

      <style jsx>{`
        .review-form-container {
          background: var(--card-bg, #1a1a2e);
          border-radius: 12px;
          padding: 24px;
          margin: 20px 0;
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
          animation: slideIn 0.3s ease-out;
        }

        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .review-form {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .form-header {
          border-bottom: 2px solid var(--border-color, #2d2d44);
          padding-bottom: 12px;
        }

        .form-title {
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--text-primary, #ffffff);
          margin: 0;
        }

        .error-message {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px;
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          border-radius: 8px;
          color: #ef4444;
          font-size: 0.875rem;
        }

        .error-icon {
          width: 20px;
          height: 20px;
          flex-shrink: 0;
        }

        .rating-section {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .rating-label {
          font-size: 1rem;
          font-weight: 600;
          color: var(--text-primary, #ffffff);
        }

        .stars-container {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }

        .star-button {
          background: none;
          border: none;
          cursor: pointer;
          padding: 4px;
          transition: all 0.2s ease;
          color: var(--star-color, #fbbf24);
        }

        .star-button:hover:not(:disabled) {
          transform: scale(1.2);
        }

        .star-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .star-button.active {
          color: var(--star-active, #f59e0b);
        }

        .star-icon {
          width: 32px;
          height: 32px;
          transition: all 0.2s ease;
        }

        .rating-display {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-top: 8px;
        }

        .rating-number {
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--accent-color, #00d4ff);
        }

        .rating-text {
          font-size: 1rem;
          color: var(--text-secondary, #a0a0b0);
        }

        .comment-section {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .comment-label {
          font-size: 1rem;
          font-weight: 600;
          color: var(--text-primary, #ffffff);
        }

        .comment-textarea {
          width: 100%;
          padding: 12px;
          background: var(--input-bg, #0f0f1e);
          border: 2px solid var(--border-color, #2d2d44);
          border-radius: 8px;
          color: var(--text-primary, #ffffff);
          font-size: 0.95rem;
          font-family: inherit;
          resize: vertical;
          transition: border-color 0.2s ease;
        }

        .comment-textarea:focus {
          outline: none;
          border-color: var(--accent-color, #00d4ff);
        }

        .comment-textarea:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .character-count {
          text-align: ${isArabic ? 'left' : 'right'};
          font-size: 0.75rem;
          color: var(--text-secondary, #a0a0b0);
        }

        .form-actions {
          display: flex;
          gap: 12px;
          justify-content: flex-end;
          margin-top: 8px;
        }

        .btn-cancel,
        .btn-submit {
          padding: 12px 24px;
          border-radius: 8px;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .btn-cancel {
          background: transparent;
          border: 2px solid var(--border-color, #2d2d44);
          color: var(--text-secondary, #a0a0b0);
        }

        .btn-cancel:hover:not(:disabled) {
          background: var(--hover-bg, #2d2d44);
          color: var(--text-primary, #ffffff);
        }

        .btn-submit {
          background: var(--accent-color, #00d4ff);
          border: none;
          color: #000000;
        }

        .btn-submit:hover:not(:disabled) {
          background: var(--accent-hover, #00b8e6);
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 212, 255, 0.3);
        }

        .btn-cancel:disabled,
        .btn-submit:disabled {
          opacity: 0.5;
          cursor: not-allowed;
          transform: none;
        }

        .spinner {
          width: 20px;
          height: 20px;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }

        @media (max-width: 640px) {
          .review-form-container {
            padding: 16px;
          }

          .form-title {
            font-size: 1.25rem;
          }

          .star-icon {
            width: 28px;
            height: 28px;
          }

          .stars-container {
            gap: 4px;
          }

          .form-actions {
            flex-direction: column-reverse;
          }

          .btn-cancel,
          .btn-submit {
            width: 100%;
            justify-content: center;
          }
        }

        /* Light mode support */
        @media (prefers-color-scheme: light) {
          .review-form-container {
            --card-bg: #ffffff;
            --text-primary: #1a1a2e;
            --text-secondary: #6b7280;
            --border-color: #e5e7eb;
            --input-bg: #f9fafb;
            --hover-bg: #f3f4f6;
          }
        }
      `}</style>
    </div>
  );
};

export default ReviewForm;

// Made with Bob
